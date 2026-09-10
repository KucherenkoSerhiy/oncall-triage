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

Amendment 2026-09-10 (M9d): the `pull_request` subject is retired in favor of `environment:plan` on both clouds.

Why `pull_request` was acceptable through M1-M8: the repository is public, so no fork ever presents a token at all (GitHub never issues an `id-token` to a workflow run from a forked repository); every PR that could authenticate was a PR of this repository, reviewed the same as any other change. But "PR plans get fewer permissions than applies" was never actually true here - `deploy.yml`'s plan job and apply job assume the *same* deploy role (docs/DESIGN.md never proposed a separate read-only plan identity; see "Non-requirements" in docs/specs/m9-hardening.md, tracked as a v2 item). A subject that any PR of this repository can present, on a role with full apply permissions, is broader than it needs to be for a job that only ever runs `terraform plan` - exactly why the subject, not the permissions, is what M9d narrows.

What changes: both trust policies drop `pull_request:*` and add `environment:plan` (classic and immutable subject forms); `deploy.yml`'s plan job declares the `plan` GitHub Actions environment (no required reviewers - it exists only to scope the subject) so its OIDC token carries that subject. `infra/bootstrap/github` (new, `integrations/github` provider) owns the `plan` and `demo` environments in Terraform. Rollout is two PRs: the bootstrap trust-policy change (applied by a human, since it touches `infra/bootstrap/*`) merges first, then the `deploy.yml` change - see `infra/README.md` "Rotating the PR subject to an environment (M9d)".

Residual risk: a PR from a fork never receives the token under either subject - GitHub only sends an environment-scoped `id-token` to a workflow run on a branch of *this* repository, and fork PRs run on the fork's own ref. The safety margin narrowed here is against a compromised branch or a malicious PR from a collaborator with write access to this repository, not against forks (which were never a threat either subject faced).

Amendment 2026-09-09 (M3b): rollback of the triage-worker image is a `workflow_dispatch` with a previous `sha-<sha>` tag, documented with the exact command in `infra/README.md`'s "Rollback" section.
