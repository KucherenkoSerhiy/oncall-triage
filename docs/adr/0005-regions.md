# 0005. AWS eu-central-1 and Azure westeurope

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D5

## Context

A European bank narrative implies EU data residency; both regions carry every service used.

## Decision

eu-central-1 for AWS, westeurope for Azure. Route 53 and CloudFront are global.

## Consequences

Cross-region latency between the estates is a few tens of milliseconds and irrelevant to alert triage.
