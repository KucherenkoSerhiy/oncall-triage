# 0008. Trunk-based delivery: plan on PR, approve, apply on merge, OIDC only

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D8

## Context

The pipeline is part of the product: it is how a bank would run this and it is what reviewers look at first. Stored cloud keys are the most common red flag.

## Decision

Short-lived branches, PR required, squash-merge. deploy.yml posts a Terraform plan on every PR, applies on merge after a required reviewer approves the demo environment, and authenticates to AWS by OIDC role and to Azure by federated credential. Container images are immutable and named by git SHA; rollback is re-running the workflow with a previous SHA.

## Consequences

No cloud credential exists in GitHub; the bootstrap that creates the OIDC trust is applied once by a human from infra/bootstrap. Every PR shows exactly what will change.

Amendment 2026-09-09: GitHub issues the *immutable* OIDC subject (`repo:owner@id/repo@id:...`) for repositories created after July 2026, and this repository is one of them. Both trust policies (AWS role, Azure federated credentials) accept the classic and the immutable subject, pinned to this owner and repository id, so a rename cannot lock the pipeline out and a wildcarded id is never used. PR plans authenticate with the `pull_request` subject for now; an environment-scoped subject (`environment:plan`) on both clouds is an M9 hardening item because changing the AWS role trust needs a bootstrap credential session.
