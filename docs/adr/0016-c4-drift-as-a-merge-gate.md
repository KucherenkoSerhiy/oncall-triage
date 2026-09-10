# 0016. C4 drift as a merge gate

- Status: accepted
- Date: 2026-09-10
- Design reference: docs/DESIGN.md section 10 ("Diagrams as code, and keeping them honest")

## Context

`docs/c4/workspace.dsl` (M0/M1) is the source-of-truth architecture model, exported to Mermaid and rendered on every PR. That only guarantees the exported diagram matches the DSL - nothing stops the DSL itself from drifting away from what's actually provisioned: a container renamed in Terraform, a Kubernetes workload added without updating the model, or a container deleted from the model while its resource lingers. M4/M5 already tag every Terraform resource with `c4_container`, and M6/M7 label every Kubernetes workload `nordwind.dev/c4-container`, precisely so a join key exists - but until now nothing read those tags back against the model.

Comparing against what's actually deployed (`terraform show -json` of live state, `kubectl get` against a running cluster) was considered and rejected: it needs cloud credentials and a running `kind` cluster in every PR check, turning an offline gate into one with external dependencies and its own flakiness. The repository's existing quality gates (checkov, tflint, kubeconform) are all static-analysis-only for the same reason.

## Decision

`scripts/c4_drift.py` computes three sets **statically**, all from files already in the repository, and compares them:

- **Model**: every `identifier = container ...` line inside a `softwareSystem` block in `workspace.dsl`, via a small tolerant line parser (not a full DSL grammar - Structurizr's own `structurizr/structurizr` image already validates syntax in the `c4` job's export step that runs first).
- **Terraform**: every `c4_container` tag value under `infra/**/*.tf`, parsed statically with `python-hcl2` (`tags = { c4_container = "x" }`, `tags = local.tags.x` resolved back through the root's `locals` block, and a provider's `default_tags` reported separately as a root-level default) - never `terraform show -json` of a plan or state, so the check needs no cloud credentials and no `terraform init`.
- **Helm**: every `nordwind.dev/c4-container` label in `helm template deploy/helm/nordwind-bank --set kafka.enabled=true` - the chart's own rendering, not a live cluster.

The join key is the **DSL identifier itself** (`cards`, not the display name `"cards-authorization"` or the Kubernetes object name), because it's the one string every container in the model already has for free - no second `tags "c4:<id>"` convention to keep in sync. Terraform's tags already matched it. Helm's labels didn't (M6/M7 stamped the kebab-case service name instead, which the identifier can't equal - `openBanking` isn't a legal DNS-1123 object name), so this milestone splits the label's value from the object name: `values.yaml` gains a `c4Container` field per service, distinct from `name`, and `_helpers.tpl` stamps that. The object/image/Secret names an operator or `kubectl` actually types stay exactly as they were.

Every container that is a cloud resource or a Kubernetes workload gets tagged `Deployable` in the DSL - which, in this model, is every container - so the drift check fails when Terraform or Helm mention a container the model doesn't declare, or a `Deployable` container appears in neither. `docs/c4/drift-allow.yaml` names the deliberate exceptions with a reason each: `dashboard` (`aws_cloudwatch_dashboard` has no `tags` argument in the AWS provider - there is no resource to tag), `appInsights` (shares the Azure `monitor` tag with Log Analytics, the storage account and the service plan rather than getting its own), and `kafkaExporter` / `prometheus` / `alertmanager` (provisioned by the Strimzi operator or the separate `kube-prometheus-stack` release, outside `deploy/helm/nordwind-bank`'s own templates). `ci.yml`'s `c4` job runs `python scripts/c4_drift.py --strict` right after the export-staleness check and pipes the Markdown table into `$GITHUB_STEP_SUMMARY`; `--strict` additionally fails the run if `helm` wasn't on PATH to produce the Helm set at all (never true in CI, which installs it), so a silently-incomplete check can't pass by accident.

## Consequences

A renamed or deleted container now fails the same PR that introduces the mismatch, with a table naming exactly which container and where, instead of surfacing later as a diagram nobody trusts. What it does **not** catch: a container correctly tagged but never actually applied (`terraform plan` never run, `helm upgrade` never invoked) - this check reads source files, not deployed state, by design (see Context). It also can't catch a tag value that's wrong on both sides in the same way - if a resource and the model agree on a stale name, the sets match and nothing fires. Both are explicitly out of scope (see the M8 spec's non-requirements); a live-state check would need a different design and its own ADR. The allow-list is reviewed the same way any other exception list in this repo is (`.checkov.yaml`'s skips, `tflint`'s ignores): a reason per entry, checked in, visible in the drift report itself so it never silently hides a real regression.
