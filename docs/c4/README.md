# C4 model

`workspace.dsl` is the single source of truth for the architecture
diagrams (Structurizr DSL). `generated/` holds the Mermaid exports that
GitHub renders; do not edit them by hand.

- Regenerate: `task c4` (needs Docker - runs the `structurizr/structurizr` image,
  then `scripts/c4_render.py` wraps the `.mmd` files into `generated/README.md`
  so GitHub renders them).
- CI (`ci.yml`) fails a pull request whose `generated/` is stale relative
  to `workspace.dsl`; `c4.yml` regenerates on the default branch.
- Views: `context` (L1), `containers` (L2, triage brain), `k8s-estate`
  (L2, Kubernetes estate), `worker-components` (L3), `deployment` (AWS,
  Azure - the `demo` environment), `deployment-kind` (the `kind`
  environment: laptop and GitHub Actions runner).
- From milestone M8, `scripts/c4_drift.py` also compares container
  identifiers in this model against `c4_container` tags in Terraform and
  labels in Helm, so a diagram that lies fails CI the same way a test does.
