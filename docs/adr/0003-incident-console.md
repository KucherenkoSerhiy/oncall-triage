# 0003. Delivery surface is a static incident console

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D3

## Context

On-call engineers need somewhere to read verdicts and teach known issues. Slack, Teams and e-mail integrations each need an external workspace and a secret.

## Decision

A static site (S3 + CloudFront) reading a small console API. Chat and e-mail become v2 adapters behind the same verdict record.

## Consequences

Zero moving parts for the demo; the verdict record is the integration point, not the UI; v1 console auth is a bearer token (ADR 0010).
