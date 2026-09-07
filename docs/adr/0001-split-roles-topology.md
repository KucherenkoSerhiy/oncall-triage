# 0001. Split roles: one triage brain on AWS, bank estates on AWS, Azure and Kubernetes

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D1

## Context

We want a realistic multi-cloud bank scenario: SRE tooling in one place, workloads everywhere. Running the triage brain symmetrically on two clouds doubles the surface, the secrets and the LLM path for no learning gain.

## Decision

The triage brain (ingest, queue, worker, store, console) runs on AWS eu-central-1 only. Three bank estates feed it: AWS serverless (Lambda + CloudWatch), Azure serverless (Functions + Azure Monitor) and a Kubernetes estate (Prometheus + Alertmanager + Kafka).

## Consequences

One LLM path to secure and pay for; each cloud does something different; the Azure and Kubernetes estates reach AWS over HTTPS with HMAC. A future Azure-hosted brain is a Terraform root module away, not a redesign.
