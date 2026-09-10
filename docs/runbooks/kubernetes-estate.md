# Runbook: the Kubernetes estate (kind)

The `nordwind-bank` chart (M6a: `cards-authorization`, `fraud-scoring`,
`open-banking-api`) plus `kube-prometheus-stack` running on
[kind](https://kind.sigs.k8s.io/) - a full Kubernetes cluster as Docker
containers. Same charts on a laptop and in `estate-demo.yml`; see ADR
[0007](../adr/0007-kubernetes-on-kind.md) for why kind, not a cloud cluster.

## Prerequisites

- **Docker Desktop** (or another Docker Engine) with **~6 GB of RAM**
  available - kind's control-plane node, kube-prometheus-stack and three
  bank services all fit, but a smaller allowance makes `--wait` steps time
  out under load.
- `kind` (pinned `v1.31.2` node image in `deploy/kind/cluster.yaml`), `helm`
  (`v3.17.1`), `task` - all three are free binaries; versions are pinned in
  `Taskfile.yml`'s `vars:` and `.github/workflows/estate-demo.yml`.
- `kubectl`, already required for the rest of the repo's Kubernetes work.
- Optional: `FORWARDER_URL` exported to your shell if you want route B to
  actually reach `bank/azure/alert_forwarder` (from a deployed `infra/azure`:
  `terraform -chdir=infra/azure output -raw forwarder_url`, sensitive).
  Leaving it unset is fine for local chaos poking - Alertmanager still fires
  and routes to a dummy receiver; `task estate-status` says so.

## `task estate-up` walkthrough

```bash
export FORWARDER_URL="$(terraform -chdir=infra/azure output -raw forwarder_url)"  # or leave unset
task estate-up
```

What happens, in order: creates the `nordwind` kind cluster if it doesn't
already exist; adds/updates the `prometheus-community` Helm repo; renders
`deploy/helm/values/kube-prometheus-stack.yaml` with `FORWARDER_URL`
substituted into the Alertmanager receiver
(`scripts/render_alertmanager_values.py`); installs `kube-prometheus-stack`
into the `monitoring` namespace; builds the three service images
(`nordwind/<service>:dev`) and `kind load`s them - no registry needed;
installs the `nordwind-bank` chart into the `bank` namespace. Expect
2-4 minutes end to end (kube-prometheus-stack's `--wait` is the slow part);
the task is idempotent - re-running it after the cluster already exists just
re-applies the Helm releases and reloads the images.

Expected tail of the output:

```
Prometheus:   http://localhost:9090
Alertmanager: http://localhost:9093
NAMESPACE    NAME                                        READY   STATUS
bank         cards-authorization-...                     1/1     Running
bank         fraud-scoring-...                            1/1     Running
bank         open-banking-api-...                         1/1     Running
monitoring   alertmanager-monitoring-...                  2/2     Running
monitoring   prometheus-monitoring-...                    2/2     Running
...
```

## The UIs

Thanks to `deploy/kind/cluster.yaml`'s `extraPortMappings` and the
NodePort Services set in `deploy/helm/values/kube-prometheus-stack.yaml`
(`prometheus.service` / `alertmanager.service`, ports 30090/30093), both UIs
are reachable with no `kubectl port-forward`:

- Prometheus: <http://localhost:9090> - alert rule state under **Alerts**,
  targets under **Status > Targets**.
- Alertmanager: <http://localhost:9093> - firing/silenced alerts, and under
  **Status** the receiver configuration (`route-b-forwarder`).

`task estate-status` prints the same firing-alert list from the terminal
(name, service, severity, `startsAt`), plus pods in `bank`/`monitoring` and
the `nordwind-faults` ConfigMap contents. `task estate-status -- --kafka`
also prints `KafkaTopic`s and per-group consumer lag (see "Kafka" below).

## Kafka (M7a)

`task estate-up` installs the Strimzi operator into `kafka` (watching only
`bank`) after kube-prometheus-stack, then waits up to 10 minutes for the
`Kafka` resource's `Ready` condition (printing the operator's log tail on
timeout). Business events flow `cards-authorization` → `card.authorized` →
`fraud-scoring` → `fraud.scored` → `open-banking-api`; see
`deploy/helm/nordwind-bank/README.md`'s Kafka section for the topic/user/ACL
table and how to tail a topic.

### Lag inspection

```bash
task estate-status -- --kafka
```

prints `kubectl get kafkatopics -n bank` and, by `kubectl exec`-ing into the
broker with the `admin` `KafkaUser`'s SCRAM credentials,
`kafka-consumer-groups.sh --describe --all-groups` - the `LAG` column per
`(GROUP, TOPIC, PARTITION)`. Under the `lag` fault (below) `fraud-scoring`'s
lag on `card.authorized` climbs steadily; healthy otherwise means at or near
0.

### `broker-down` recovery

`broker-down` is a chaos *action* against the platform, not a service fault
mode: it scales the `broker` `KafkaNodePool` to 0 replicas (the separate
`controller` pool - the KRaft metadata quorum - is left alone; Strimzi
refuses to reconcile a cluster whose node pools are all at 0 replicas, so a
single combined pool can't be scaled to 0 this way), so every
producer/consumer in the estate starts failing to reach the broker while
staying up themselves (`/healthz` unaffected).

```bash
task chaos-k8s -- kafka broker-down
task estate-status   # broker pod Terminating/gone; KAFKA_BOOTSTRAP unreachable
task chaos-k8s -- kafka clear   # scales back to 1 and waits for the broker pod Ready
```

`bankops chaos --estate kubernetes kafka --mode broker-down` / `--clear` do
the same thing (`cli/bankops/commands.py` calls the same
`scripts/chaos_k8s.py` functions).

## Chaos cookbook

Inject a fault with `task chaos-k8s -- <service> <mode>` (or
`bankops chaos --estate kubernetes <service> --mode <mode>`); clear it with
`task chaos-k8s -- <service> clear`. Expected time-to-verdict assumes
`FORWARDER_URL` is set and the AWS spine is live - **~6-9 minutes**: the
`for:` duration on each rule (2-3 min) plus Alertmanager's `group_wait`
(10s), the forwarder hop, and one triage-worker invocation.

| Service | Mode | Rule | `for` |
|---|---|---|---|
| `cards-authorization` | `timeouts` | `CardsAuthHighLatency` (p99 > 1s) | 2m |
| `cards-authorization` | `issuer-down` | `CardsAuthErrorRatio` (error ratio > 0.5) | 2m |
| `fraud-scoring` | `model-drift` | `FraudScoreDrift` (mean score > 0.6) | 3m |
| `fraud-scoring` | `crashloop` | `FraudScoringCrashLoop` (restarts > 2 / 10m) | - |
| `open-banking-api` | `rate-limit-storm` | `OpenBankingRateLimitStorm` (429 ratio > 0.5) | 2m |
| `open-banking-api` | `cert-expiry` | `OpenBankingCertExpiringSoon` (< 14d to expiry) | - |

```bash
task chaos-k8s -- cards-authorization timeouts
task estate-status   # watch CardsAuthHighLatency go from pending to firing
task chaos-k8s -- cards-authorization clear
```

`task estate-demo` runs the `cards-timeouts` scenario
(`scripts/estate_scenarios.py`) end to end unattended: sets the fault, waits
for `CardsAuthHighLatency` to fire in Alertmanager (budget 480s), waits for
a verdict on the console API (budget 600s), prints it, and clears the fault
in a `finally` regardless of outcome.

## Reading `estate-demo` artifacts

Every `estate-demo.yml` run (manual or the Sunday 06:00 UTC schedule)
uploads `estate-demo-<run id>` with, `if: always()`:

- `alertmanager-alerts.json` - `GET /api/v2/alerts`, every alert Alertmanager
  held at teardown time (firing, pending, or resolved).
- `prometheus-rules.json` - `GET /api/v1/rules`, every rule's current
  evaluation state; a rule stuck `pending` past its `for:` duration, or
  never leaving `inactive`, points at the metric side (check the service's
  `/metrics`) rather than the alert-delivery side.
- `<service>.log` for each of the three services - the ticker's normal
  output plus, in `crashloop` mode, the `sys.exit(1)` and restart.
- `events.txt` - the last 100 cluster events by timestamp; a good first stop
  for `ImagePullBackOff` / `CrashLoopBackOff` / scheduling failures that
  never reach the rule-evaluation stage at all.

A red run with no artifact at all means `task estate-up` itself failed
(cluster creation or the Helm installs) - check the job log's `estate-up`
step directly.

## Teardown

```bash
task estate-down   # kind delete cluster --name nordwind
```

Safe to run even if the cluster doesn't exist. `estate-demo.yml` always runs
this in its final step regardless of how the scenario went.
