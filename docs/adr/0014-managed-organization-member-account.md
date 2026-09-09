# 0014. Workloads live in a member account of the owner's AWS Organization; AWS-managed guardrails are kept

- Status: accepted
- Date: 2026-09-09
- Design reference: docs/DESIGN.md, decision D5 (amended)

## Context

The AWS account was created through AWS's new sign-up experience (Builder ID, "projects"). AWS provisions an Organization on the owner's behalf: a management account, a delegated-admin account and the project account, with AWS-managed service control policies - a region floor (home region plus global services) and a deny on identity federation. The first bootstrap attempt failed on both. Advanced features were activated (irreversible), which made the owner the administrator of that Organization and lifted the federation deny; the region floor remained.

## Decision

Run every workload in the project account (373665158010) as a member account; leave the management account empty and used only for organization-level administration. Keep the AWS-managed region floor rather than editing it, and move the design's AWS home region from eu-central-1 to eu-north-1 (Stockholm), which the floor allows together with the global services the design needs (Route 53, CloudFront, ACM in us-east-1, Budgets, IAM).

## Consequences

The account layout is the one a bank would expect - workloads never in the management account, guardrails authored above the workload account. Any future region change means editing the `RegionFloor` statement of the managed SCP from the management account, deliberately. `s3:ListAllMyBuckets` is denied by the floor (it is a global call); nothing in the design relies on it. The bootstrap identity (`nordwind-bootstrap` IAM user) is deleted after the bootstrap; all later applies use the OIDC deploy role.
