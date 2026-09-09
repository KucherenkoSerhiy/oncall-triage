# `nordwind-bank` Helm chart

Deploys the three Kubernetes bank services (`bank/k8s/cards_authorization`,
`bank/k8s/fraud_scoring`, `bank/k8s/open_banking_api`) as one Deployment +
Service + ServiceMonitor each, a shared fault-injection ConfigMap, and a
`PrometheusRule` with the six alert rules that make the estate's chaos
scenarios observable. M6a ships the chart and its offline gates (`helm
lint`, `helm template | kubeconform`, `trivy config`); M6b (kind, `task
estate-up`, `estate-demo.yml`) is what actually installs it onto a live
cluster.

## Values

| Value | Default | Purpose |
| --- | --- | --- |
| `imageTag` | `latest` | Tag applied to `nordwind/<service>:<imageTag>`. `imagePullPolicy: IfNotPresent` so `kind load docker-image` works without a registry. |
| `forwarder.url` | `""` | Not read by this chart directly - kept here so `--set forwarder.url=...` is the one flag M6b needs for the whole estate. The value that actually matters lives in `deploy/helm/values/kube-prometheus-stack.yaml`'s Alertmanager config, substituted by `scripts/render_alertmanager_values.py`. |
| `kafka.enabled` | `false` | Accepted, unused until M7. |
| `monitoring.release` | `monitoring` | Stamped as the `release` label on the `ServiceMonitor`/`PrometheusRule` objects (see "How Prometheus finds these objects" below). Must match the Helm release name kube-prometheus-stack is installed under. |
| `services` | the three service names | List of `{name}` objects the Deployment/Service/ServiceMonitor templates range over. Not meant to be overridden - a fourth k8s bank service is a chart change, not a values change. |

## How faults reach pods

One ConfigMap, `nordwind-faults`, with one key per service
(`cards-authorization`, `fraud-scoring`, `open-banking-api`), each key
empty by default. Each service's Deployment mounts the ConfigMap at
`/etc/nordwind` but projects only **its own** key, via `items` +
`path: fault`:

```yaml
volumes:
  - name: faults
    configMap:
      name: nordwind-faults
      items:
        - key: cards-authorization
          path: fault
```

So every pod always reads the same path, `/etc/nordwind/fault`, but each
service's Deployment wires it to a different ConfigMap key. `bankops chaos
--estate kubernetes` (M6b) patches the relevant key; `bank/k8s/_shared/faults.py`
re-reads the mounted file at most once every 5 seconds.

## How Prometheus finds these objects

`deploy/helm/values/kube-prometheus-stack.yaml` sets
`serviceMonitorSelectorNilUsesHelmValues: false` and
`ruleSelectorNilUsesHelmValues: false`, which makes kube-prometheus-stack's
Prometheus select **every** ServiceMonitor/PrometheusRule cluster-wide
(the nil selector, used as-is, matches everything) rather than only ones
labelled with its own release name. That's the primary mechanism this
chart relies on. The `release: {{ .Values.monitoring.release }}` label on
the `ServiceMonitor` and `PrometheusRule` objects is kept anyway, as a
second, redundant path: if the upstream values ever revert those two
flags to their (more restrictive) defaults, kube-prometheus-stack's
default selector behaviour is to require exactly that label, and these
objects would still be picked up with no chart change needed.

## How rules map to services and severities

Group `nordwind-bank.rules`, six alerts, each labelled `service` +
`severity` and annotated `summary` + `description`:

| Alert | Service | Severity | Fires when |
| --- | --- | --- | --- |
| `CardsAuthHighLatency` | cards-authorization | high | p99 of `cards_auth_request_seconds` > 1s for 2m |
| `CardsAuthErrorRatio` | cards-authorization | critical | `result="error"` ratio > 50% for 2m |
| `FraudScoreDrift` | fraud-scoring | high | mean `fraud_score_bucket` observation > 0.6 for 3m |
| `FraudScoringCrashLoop` | fraud-scoring | high | container restarts increase by > 2 over 10m |
| `OpenBankingRateLimitStorm` | open-banking-api | warning | `code="429"` ratio > 50% for 2m |
| `OpenBankingCertExpiringSoon` | open-banking-api | warning | `openbanking_cert_expiry_seconds` < 14 days away |

`for` durations are short on purpose - M6b's chaos scenarios need to reach
a verdict in a handful of minutes, not hours.

## What M6b adds

Everything that needs a live cluster: `deploy/kind/cluster.yaml`, the
`task estate-up` / `estate-down` / `estate-status` / `chaos-k8s` Taskfile
targets (including running `scripts/render_alertmanager_values.py` and
`helm upgrade --install`), `.github/workflows/estate-demo.yml`, and
`docs/runbooks/kubernetes-estate.md`.
