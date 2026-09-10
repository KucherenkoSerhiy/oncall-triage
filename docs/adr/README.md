# Architecture decision records

One record per decision row in [DESIGN.md](../DESIGN.md) section 2. Format: lightweight MADR. A new record is added whenever a decision changes; old ones are superseded, never edited.

| # | Decision |
|---|---|
| [0001](0001-split-roles-topology.md) | Split roles: one triage brain on AWS, bank estates on AWS, Azure and Kubernetes |
| [0002](0002-terraform-and-helm.md) | Terraform for cloud resources, Helm for in-cluster software |
| [0003](0003-incident-console.md) | Delivery surface is a static incident console |
| [0004](0004-claude-via-litellm.md) | Triage agents run on Claude Haiku 4.5 through ADK's LiteLLM adapter |
| [0005](0005-regions.md) | AWS eu-north-1 (Stockholm) and Azure swedencentral (Stockholm) |
| [0006](0006-kubernetes-and-kafka.md) | Kubernetes and Kafka are part of the bank |
| [0007](0007-kubernetes-on-kind.md) | The Kubernetes estate runs in kind, not a managed cloud cluster |
| [0008](0008-delivery-pipeline.md) | Trunk-based delivery: plan on PR, approve, apply on merge, OIDC only |
| [0009](0009-custom-domain.md) | triage.serhiykucherenko.dev with a Route 53 subdomain zone |
| [0010](0010-console-auth-bearer-token.md) | Console authentication v1 is a bearer token |
| [0011](0011-diagrams-as-code.md) | Structurizr DSL is the source of truth for architecture diagrams |
| [0012](0012-public-repo-and-nightly-demo.md) | Repository goes public at M2; the estate demo runs nightly |
| [0013](0013-showcase-quality-bar.md) | Showcase first: every milestone ships tests, docs and updated diagrams |
| [0014](0014-managed-organization-member-account.md) | Workloads live in a member account of the owner's AWS Organization; AWS-managed guardrails are kept |
| [0015](0015-route-a-relay-instead-of-a-public-kafka-endpoint.md) | Route A relay instead of a public Kafka endpoint |
| [0016](0016-c4-drift-as-a-merge-gate.md) | C4 drift as a merge gate |
| [0017](0017-runbooks-derived-from-incidents.md) | Runbooks derived from incidents |
