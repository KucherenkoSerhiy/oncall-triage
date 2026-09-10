# M6a decisions

Minimal choices made where the spec left room, for the record.

## M6b additions

- **`bank/faults.py` is host-side only.** The spec asks for one shared
  `VALID_MODES` table for `bankops chaos --estate kubernetes` and
  `task chaos-k8s`. The per-service `VALID_MODES` tuples in
  `bank/k8s/<service>/service.py` stay as they are (used by `FaultFile` to
  warn on an unrecognised ConfigMap value) rather than importing the new
  module: each service's Docker image copies only `_shared/` and its own
  service directory (M6a's sibling-import trick), not the repo root, so
  `bank/faults.py` would not exist inside the container. The new module is
  a small, deliberate duplication scoped to the two host-side tools that
  actually need a shared table.
- **kind node image digest**: pinned to kind's own published v0.25.0
  release image, `kindest/node:v1.31.2@sha256:18fbefc2...` (full digest in
  `deploy/kind/cluster.yaml` and `Taskfile.yml`'s `KIND_NODE_IMAGE` var) -
  verified against `kubernetes-sigs/kind`'s GitHub release notes rather than
  guessed, since a wrong digest fails cluster creation outright.
- **`scripts/estate_scenarios.py`'s two-hop wait, one message set**: the
  spec names three possible failures ("rule never fired / Alertmanager
  never delivered / no verdict") but only two budgets (`--alert-timeout`,
  `--verdict-timeout`). `wait_for_rule_firing` owns the first message;
  `wait_for_spine_verdict` tracks whether it has ever seen a matching alert
  at all (regardless of verdict) and picks "never delivered" vs "no
  verdict" from that single flag when its one budget expires - no third
  budget needed.
- **C4 (`docs/c4/workspace.dsl`)**: the model already had `kafka`,
  `alerts-bridge` and `kafka-relay` inside `k8sEstate` (drafted ahead of
  M7, presumably from the original whole-estate DESIGN.md sketch) and a
  single `demo` deployment environment nesting the kind clusters alongside
  AWS/Azure. Non-requirement 1 for this milestone ("Kafka/Strimzi and
  route A (M7)") means those containers/relationships come out now, not
  just get left stale; they return in M7. The kind laptop/GitHub-runner
  deployment nodes moved out of `demo` into their own `deploymentEnvironment
  "kind"` (a second deployment view, `deployment-kind`) per requirement 7's
  explicit wording, rather than nesting them inside `demo` as before.
- **`k8sEstate` drops out of the `context` (system context) view**: with
  `kafka-relay -> triage.ingest` gone, the model has no relationship path
  from `k8sEstate` to `triage` at all until M7 - the only route out today is
  `k8sEstate.alertmanager -> azureEstate.forwarder`, one hop short of
  `triage`. That is an accurate statement about the current architecture
  (a Kubernetes alert cannot reach the spine without the Azure forwarder
  yet), not a rendering bug, so the context view is left as Structurizr
  computes it rather than forcing `k8sEstate` back in with an `include`.

- **Where the ticker thread lives vs. where the process exits**: the ticker
  (`bank/k8s/_shared/ticker.py`) runs `work()` on a background daemon
  thread, as the spec's "in-process ticker thread" wording implies. But an
  uncaught `SystemExit` raised on a non-main thread only kills that thread,
  not the process - it wouldn't produce the CrashLoopBackOff the
  `crashloop` fault is meant to demonstrate. The ticker catches
  `SystemExit` from `work()` and converts it to `os._exit(code)`, so the
  fault behaves the same regardless of which thread calls `sys.exit(1)`.
- **`FaultFile` constructor**: the spec shows `FaultFile(path=..., ttl=5)`.
  Each service has a different set of valid modes, and "unknown mode"
  needs *something* to check against, so `FaultFile` takes an optional
  `valid_modes: Iterable[str] = ()` keyword (empty = accept anything) -
  additive to the two required params, not a change to them.
- **Image entrypoint layout**: each Dockerfile copies `bank/k8s/_shared/`
  and `bank/k8s/<service>/` into the image as top-level siblings
  (`/app/_shared`, `/app/<service>`), so `python -m <service>` matches the
  spec literally and the sibling-import trick works the same way M5a's
  Azure Functions apps use it - `_shared` is a top-level package in the
  deployed artifact but nested under `bank.k8s` in the repo. Only the
  `_shared` import needs the `try/except` fallback; each service's
  `__main__.py` importing its own `service.py` uses a plain relative
  import (`from .service import ...`), since that resolves correctly
  under both layouts without needing to know its own full package name.
- **ServiceMonitor/PrometheusRule selectors**: the spec offers two ways to
  make kube-prometheus-stack pick these objects up - a `release: monitoring`
  label, or opening the selectors in `ruleSelectorNilUsesHelmValues` /
  `serviceMonitorSelectorNilUsesHelmValues`. Did both: the open selectors
  (requirement 3) are the mechanism actually relied on, and the label is
  kept as a documented, redundant fallback - see
  `deploy/helm/nordwind-bank/README.md`.
- **`openbanking_cert_expiry_seconds` recomputed every tick**: rather than
  fixing an expiry timestamp once at startup, `work()` sets the gauge to
  `clock() + offset` on every call - offset is 90 days normally, 3 days
  under `cert-expiry`. Simpler than tracking a fixed expiry date, and
  behaves the same for `OpenBankingCertExpiringSoon` either way (the
  distance to "now" stays constant while the fault mode is active).
- **CI tool versions pinned in `ci.yml`'s `helm` job**: `helm` v3.17.1
  (`azure/setup-helm@v4`), `kubeconform` v0.6.7, `trivy` v0.58.1 - latest
  stable releases as of M6a. `helm-check`/`helm-lint` Taskfile targets
  mirror the same commands for local use (kubeconform/trivy aren't
  installed by `task install`; a contributor running `task helm-check`
  needs them on PATH already, same as `terraform`/`tflint`/`checkov` for
  `task tf:*`).

## M7b additions

- **`alerts-bridge`'s Service is release-name-prefixed; the other four
  aren't.** `deploy/helm/values/kube-prometheus-stack.yaml` is a values
  file for a *different* Helm release (`monitoring`) and can't read
  `nordwind-bank`'s `.Release.Name`, so its webhook URL has to be a literal
  string. Rather than hardcode `nordwind-bank-alerts-bridge` in the
  template too (a second, silently-driftable place naming the same
  release), the Service's `metadata.name` is `{{ .Release.Name }}-alerts-bridge`
  - correct as long as `Taskfile.yml`'s `estate-up` keeps installing this
  chart under the release name `nordwind-bank`, same assumption the Kafka
  bootstrap hostname already makes.
- **`alerts-bridge`/`kafka-relay` are not in `.Values.services`.** That
  list drives the generic `templates/{deployment,service,servicemonitor}.yaml`
  loop, which mounts the fault ConfigMap and is rendered unconditionally.
  Both new services need Kafka credentials unconditionally (no fault mode
  of their own) and must not render at all when `kafka.enabled=false`, so
  they get their own templates under `templates/kafka/` instead of joining
  the loop.
- **`render_alertmanager_values.py --kafka/--no-kafka` swaps a marked block
  by exact string match, not by parsing YAML and re-dumping it.** The rest
  of the file's existing tests assert on literal text (comments, formatting
  survive rendering); re-serializing through `yaml.safe_dump` would pass
  those tests' *behaviour* but silently drop every comment in the file.
  Two marker comments (`__ROUTE_KAFKA_BLOCK_START__` / `_END__`) bracket the
  `route:`/`receivers:` block; `kafka=True` (default) just strips the
  markers, `kafka=False` replaces the whole bracketed block with the M6
  routing.
- **Alertmanager's route-A default drops the M6-era `null` receiver and
  service-name filter entirely** (see `deploy/helm/values/kube-prometheus-stack.yaml`
  and the M7b spec's requirement 3, quoted literally: "default receiver
  `route-a-kafka`"). Every alert - including Kubernetes control-plane noise
  that `defaultRules.rules` doesn't already silence - now flows through
  `alerts-bridge` → Kafka → `kafka-relay` → ingest unless it matches one of
  the four Kafka-alert names. `--no-kafka` keeps the old shape (everything
  to `route-b-forwarder`, no Kafka receiver) since that's the literal "M6
  routing" the spec asks for when there's no `alerts-bridge` to webhook to.
- **`estate-demo.yml`'s AWS-credentials step moved before `task estate-up`.**
  M7b's `estate-up` now creates the `nordwind-ingest` Secret from an SSM
  parameter before installing the chart (kafka-relay's Deployment needs it
  to reach Ready), so the OIDC role has to exist first - previously AWS
  credentials were only configured after the cluster was already up, purely
  to read `SMOKE_TOKEN`.
- **`broker-down`'s final wait gets its own 300s budget**, separate from
  `chaos_k8s.py`'s own 180s `kubectl wait` default: the spec calls it out
  explicitly ("budget 5 min") as distinct from the alert-firing/verdict
  budgets `fraud-lag` and `broker-down` otherwise share with `cards-timeouts`.
  `scripts/estate_scenarios.py` calls `chaos_k8s.scale_kafka_node_pool` and
  `chaos_k8s.wait_for_broker_ready(timeout="300s")` directly rather than
  `chaos_k8s.kafka_clear()`, which hardcodes 180s.
