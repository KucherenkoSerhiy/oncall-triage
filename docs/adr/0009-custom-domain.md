# 0009. triage.serhiykucherenko.dev with a Route 53 subdomain zone

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D9

## Context

This is a portfolio project; a real hostname with a real certificate is part of the showcase. The parent domain is hosted elsewhere.

## Decision

A Route 53 hosted zone for triage.serhiykucherenko.dev, delegated once by four NS records at the parent's DNS. The console lives at the apex of that zone, the console API and webhooks at api.triage.serhiykucherenko.dev. Certificates come from ACM with DNS validation in the same zone.

## Consequences

About $0.50 per month; one manual step (the NS delegation) that Terraform can also perform if the parent is on Cloudflare; every other DNS record is Terraform.
