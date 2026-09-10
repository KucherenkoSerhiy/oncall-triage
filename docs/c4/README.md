# C4 model

`workspace.dsl` is the single source of truth for the architecture
diagrams (Structurizr DSL). `generated/` holds the Mermaid exports that
GitHub renders; do not edit them by hand.

## The loop: model -> export -> render -> drift

1. **Model.** Edit `workspace.dsl`: containers, relationships, views. Every
   container that is a cloud resource or a Kubernetes workload carries the
   `Deployable` tag - `scripts/c4_drift.py` (step 4) only holds those to
   account.
2. **Export.** `structurizr/structurizr` (Docker) turns the DSL into one
   `.mmd` file per view under `generated/`.
3. **Render.** `scripts/c4_render.py` wraps those `.mmd` files into
   `generated/README.md` so GitHub renders them inline.
4. **Drift.** `scripts/c4_drift.py` (M8) reads the model's container
   identifiers back against every `c4_container` tag under `infra/**/*.tf`
   and every `nordwind.dev/c4-container` label `helm template
   deploy/helm/nordwind-bank` renders, and fails if a `Deployable`
   container is missing from both, or if Terraform/Helm mention a
   container the model never declared. `docs/c4/drift-allow.yaml` lists
   the deliberate exceptions, with a reason each; see [ADR
   0016](../adr/0016-c4-drift-as-a-merge-gate.md) for what this does and
   does not catch.

`task c4` runs steps 2-3; `task c4-drift` runs step 4. `ci.yml`'s `c4` job
runs both (plus a check that `generated/` isn't stale) on every PR;
`c4.yml` re-runs steps 2-3 and commits the result on the default branch.

## Adding a container

1. Declare it in `workspace.dsl` (`identifier = container "Name"
   "Description" "Technology" "Tags"`) inside the right `softwareSystem`
   block, tagged `Deployable` if it's a real cloud resource or Kubernetes
   workload.
2. Tag the resource: a `c4_container = "<identifier>"` Terraform tag, or -
   for a Kubernetes workload in `deploy/helm/nordwind-bank` - a
   `nordwind.dev/c4-container: <identifier>` label (see
   `templates/_helpers.tpl`'s `c4Container` value, distinct from the
   object's kebab-case `name`).
3. `task c4` to regenerate the diagrams, `task c4-drift` to confirm the
   new container joins up. If it deliberately can't be tagged (like
   `dashboard`, `aws_cloudwatch_dashboard` has no `tags` argument),
   document it in `drift-allow.yaml` instead.

## Views

`context` (L1), `containers` (L2, triage brain), `aws-estate` /
`azure-estate` / `k8s-estate` (L2, one per bank estate), `worker-components`
(L3), `route-a` / `route-b` (dynamic, the two ways an alert reaches the
triage brain from Kubernetes), `deployment` (AWS, Azure - the `demo`
environment), `deployment-kind` (the `kind` environment: laptop and GitHub
Actions runner). One line of purpose per view lives in
`generated/README.md`'s own headings.
