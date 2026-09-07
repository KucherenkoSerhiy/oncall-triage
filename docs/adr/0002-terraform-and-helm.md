# 0002. Terraform for cloud resources, Helm for in-cluster software

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D2

## Context

The project spans AWS, Azure and Kubernetes. Native tools (CDK, Bicep, kubectl apply) would mean three toolchains.

## Decision

Terraform (one language, both cloud providers) for everything that has a cloud API; Helm charts for what runs inside Kubernetes. Terraform's helm provider is deliberately not used so the charts stay runnable with plain `helm` on a laptop.

## Consequences

Two tools to learn instead of four; Terraform state lives in S3 for both clouds; drift between Terraform, Helm and the C4 model is checked in CI (ADR 0011).
