# M6a decisions

Minimal choices made where the spec left room, for the record.

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
