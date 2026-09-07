# 0007. The Kubernetes estate runs in kind, not a managed cloud cluster

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D7

## Context

Kubernetes is free; the VM under a managed cluster is what costs money (about $36-72 per month for one small node, or about $3 per month per-session with a forgot-to-destroy risk). The cloud budget is $10 per month.

## Decision

One Helm chart and one set of values run in three places: kind on the laptop for development, kind inside GitHub Actions for the repeatable demo (estate-demo.yml), and optionally AKS (infra/azure-aks, v2) when a real cloud cluster is wanted.

## Consequences

$0 for Kubernetes. AWS cannot reach the in-cluster Kafka, so the hop out of Kafka is a relay pod that POSTs over HTTPS with HMAC rather than a Lambda Kafka event source; that trick returns unchanged with the AKS module. Docker Desktop needs about 6 GB of RAM.
