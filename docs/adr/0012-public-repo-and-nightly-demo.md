# 0012. Repository goes public at M2; the estate demo runs nightly

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D12

## Context

The repository is the portfolio. GitHub Actions minutes are unlimited for public repositories and the nightly demo is the regression suite for the whole bank.

## Decision

Make the repository public once the alert spine (M2) exists so that the first impression is a working system. estate-demo.yml runs on a schedule as well as on demand.

## Consequences

Everything committed must be fit to be read by a stranger from M2 on: no secrets, no TODO-driven code, no stale docs.
