# oncall-triage — Nordwind Bank alert triage

[![ci](https://github.com/KucherenkoSerhiy/oncall-triage/actions/workflows/ci.yml/badge.svg)](https://github.com/KucherenkoSerhiy/oncall-triage/actions/workflows/ci.yml)
[![deploy](https://github.com/KucherenkoSerhiy/oncall-triage/actions/workflows/deploy.yml/badge.svg)](https://github.com/KucherenkoSerhiy/oncall-triage/actions/workflows/deploy.yml)
[![estate-demo](https://github.com/KucherenkoSerhiy/oncall-triage/actions/workflows/estate-demo.yml/badge.svg)](https://github.com/KucherenkoSerhiy/oncall-triage/actions/workflows/estate-demo.yml)
[![license](https://img.shields.io/badge/license-MIT-0f766e)](LICENSE)

An LLM-powered alert-triage service for a fictional bank, built the way a
bank would have to build it: three-role agent workflow on Google ADK
(Claude Haiku 4.5 underneath), one triage brain on AWS, three monitored
estates feeding it — serverless on AWS, serverless on Azure, and a
Kubernetes estate with Prometheus, Alertmanager and Kafka — all of it
Terraform and Helm, deployed only by GitHub Actions over OIDC, with C4
diagrams that CI keeps honest. Cloud budget: under $10 a month.

> **Status:** the alert spine is live at [triage.serhiykucherenko.dev](https://triage.serhiykucherenko.dev)
> (M2); the Claude-backed triage worker is in review (M3) — see the roadmap.

## What it does

An alert arrives — from a CloudWatch alarm, an Azure Monitor rule, a
Prometheus rule travelling over Kafka, or the `bankops` chaos client. It is
normalised to one canonical shape, scrubbed of card numbers and IBANs,
de-duplicated, and queued. A triage agent pulls the alert's context and
checks a persistent **known-issues memory**:

- **known** → the reporter answers in one terse line, no page;
- **new** → a tool-less researcher characterises it (cause category,
  severity, next diagnostic step) and the reporter writes the full report
  with a page/monitor recommendation.

Engineers **teach** the system from the incident console ("this error in
payments is expected because…") and the next occurrence short-circuits.
The routing is genuine ADK dynamic delegation — the model chooses the
hand-off from what the store returned, not a fixed pipeline.

## Architecture in one picture

The C4 model lives in [`docs/c4/workspace.dsl`](docs/c4/workspace.dsl) and
is exported to [`docs/c4/generated/`](docs/c4/generated/) by CI (context,
containers, the Kubernetes estate, worker components, deployment). The
full design — decisions, cost model, security posture, pipelines,
milestones — is [`docs/DESIGN.md`](docs/DESIGN.md); each decision has an
ADR in [`docs/adr/`](docs/adr/).

```mermaid
flowchart LR
  subgraph estates["three bank estates"]
    A["AWS serverless<br/>payments · ledger · auth<br/>CloudWatch → SNS"]
    Z["Azure serverless<br/>customer-notifications<br/>Azure Monitor → forwarder"]
    K["Kubernetes (kind)<br/>cards · fraud · open-banking<br/>Prometheus → Kafka → relay"]
  end
  A & Z & K -->|"canonical alert, HMAC"| IN["ingest"]
  IN --> Q["SQS"] --> W["triage worker<br/>ADK · Claude"] --> DB[("DynamoDB<br/>alerts · verdicts · known issues")]
  DB --> UI["incident console<br/>triage.serhiykucherenko.dev"]
  CLI["bankops CLI<br/>fire · chaos · teach"] -.-> A & Z & K & IN
```

## Try the agent locally (phase 1)

```bash
pip install -r requirements.txt
cp .env.example oncall_triage/.env       # add your model API key
adk web                                  # then: "check payments-service logs"
```

Details, prompts, the three sequence diagrams and a recorded demo
transcript: [`docs/agent.md`](docs/agent.md), [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`DEMO.md`](DEMO.md).

## Roadmap

| M | Milestone | Status |
|---|---|---|
| M0 | Repo, CI, design, ADRs, C4 model | ✅ |
| M1 | Pipelines + bootstrap: Terraform roots, OIDC to both clouds, budgets, plan-on-PR / approve / apply | ✅ (first apply 2026-09-09) |
| M2 | Alert spine without LLM: ingest → DynamoDB → SQS, console + API, `bankops fire`, custom domain | ✅ live at [triage.serhiykucherenko.dev](https://triage.serhiykucherenko.dev) (2026-09-09) |
| M3 | Triage worker on Lambda (ADK + Claude), known-issue store on DynamoDB, teach from console, rollback by SHA | ✅ live (2026-09-09): real Claude verdicts via the image-based worker, smoke asserts a model verdict + a known-issue short-circuit |
| M4 | AWS estate: three services + CloudWatch alarms + chaos | ✅ live (2026-09-10): `bankops chaos payments --mode pool` -> CloudWatch alarm -> verdict `known, ack` in ~4 min, unattended ([#18](https://github.com/KucherenkoSerhiy/oncall-triage/issues/18)) |
| M5 | Azure estate: Functions + Azure Monitor + alert forwarder + chaos | ✅ live (2026-09-10, swedencentral): `bankops chaos customer-notifications --mode provider-429` -> Azure Monitor rule -> forwarder -> verdict `page` in ~7 min ([#20](https://github.com/KucherenkoSerhiy/oncall-triage/issues/20)) |
| M6 | Kubernetes estate on kind: Helm chart, Prometheus/Alertmanager, route B, `estate-demo.yml` | ✅ live (2026-09-10): `estate-demo.yml` builds a kind cluster on a GitHub runner, faults cards-authorization, and the Prometheus alert reaches a verdict `page` through route B in one 20-min job ([#22](https://github.com/KucherenkoSerhiy/oncall-triage/issues/22)) |
| M7 | Kafka backbone: Strimzi, topics, alerts-bridge + kafka-relay (route A), consumer-lag alerts | 🔨 Strimzi + wiring merged ([#23](https://github.com/KucherenkoSerhiy/oncall-triage/issues/23)); route A in progress ([#24](https://github.com/KucherenkoSerhiy/oncall-triage/issues/24)) |
| M8 | C4 drift check against Terraform tags and Helm labels | ⏳ [#25](https://github.com/KucherenkoSerhiy/oncall-triage/issues/25) |
| M9 | Hardening: self-observability + SLO, Route 53 DNSSEC + query logs (M9c), runbooks, rollback drill | ⏳ [#26](https://github.com/KucherenkoSerhiy/oncall-triage/issues/26)–[#30](https://github.com/KucherenkoSerhiy/oncall-triage/issues/30) |

Every milestone has an offline gate CI runs and a live probe recorded in
its pull request — the definition of done is in the
[PR template](.github/PULL_REQUEST_TEMPLATE.md). Work is tracked as
[GitHub milestones](https://github.com/KucherenkoSerhiy/oncall-triage/milestones)
with one issue per pull-request-sized slice (`M5a`, `M5b`, ...); the
specs the slices are built from live in [`docs/specs/`](docs/specs/).

## Repository map

```
oncall_triage/     the ADK agents and tools (phase 1, live-verified)
tests/             wiring + store tests (no API key needed)
infra/             Terraform: bootstrap (once, by hand) and the CI-applied roots — see infra/README.md
docs/              DESIGN.md · adr/ · c4/ (Structurizr DSL + generated Mermaid) · agent.md
.github/           ci.yml · deploy.yml · c4.yml · PR template · dependabot
Taskfile.yml       task test | lint | tf:validate | tf:lint | tf:scan | c4 | agent
```

## Working on it

```bash
task install      # dev dependencies + pre-commit hooks
task test         # ruff, mypy, pytest — what ci.yml runs
task tf:validate  # fmt, init (no backend), validate every Terraform root
task c4           # regenerate diagrams from the model (Docker)
```

Conventions: trunk-based, pull requests only, squash-merge, conventional
commits; a plan comment on every infrastructure PR; no cloud credential
ever stored in GitHub. License: [MIT](LICENSE).
