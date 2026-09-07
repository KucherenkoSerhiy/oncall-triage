# 0013. Showcase first: every milestone ships tests, docs and updated diagrams

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D13

## Context

A reviewer skimming the repository must find no 'no tests', 'no CI' or 'stale docs' red flag. Technology choices (Terraform, Kubernetes, Kafka, OIDC) were made for that reason as much as for the bank scenario.

## Decision

A milestone is done only when its offline gate runs in CI, its live probe is recorded in the PR, its ADR (if a decision changed) is written, and task c4 produces no diff. The PR template carries this as a checklist.

## Consequences

Slower milestones, no debt; the definition of done is enforced by the template and by CI, not by memory.
