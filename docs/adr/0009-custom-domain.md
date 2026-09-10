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

## Amendment 2026-09-09

The NS delegation is no longer a manual step. `infra/aws/dns_delegation.tf` writes the four NS records for `triage` into the Cloudflare parent zone through the `cloudflare/cloudflare` provider (`for_each` over `aws_route53_zone.triage.name_servers`, so a recreated zone re-delegates itself). The provider authenticates with the `CLOUDFLARE_API_TOKEN` repository secret, a token scoped to Zone:Read + DNS:Edit on the parent zone only; it is passed to both the plan and the apply step of `deploy.yml`.

## Amendment 2026-09-10 (M9c): DNSSEC

The zone is now DNSSEC-signed (`infra/aws/dnssec.tf`): an asymmetric KMS key in us-east-1 (a Route 53 requirement, ~$1/month - the one deliberate cost increase in the M9 hardening milestone) backs a key-signing key, and the resulting DS record is published at the parent zone on Cloudflare via the same `cloudflare/cloudflare` provider the NS delegation already uses, so the chain of trust is entirely Terraform-managed end to end. Ordering is load-bearing both ways: the DS record `depends_on` zone signing being enabled (create), and the same dependency makes Terraform remove the DS *before* disabling signing (destroy) - a DS pointing at unsigned/removed keys breaks resolution for the whole zone. The chain only validates fully once the parent `serhiykucherenko.dev` is also signed at Cloudflare - that is a manual step outside this repository's control (Cloudflare owns the parent zone), noted in `infra/README.md` "DNSSEC". Query logging (`aws_route53_query_log` to a us-east-1 CloudWatch Logs group, 7-day retention) ships alongside it, since both need the same us-east-1 plumbing. See `docs/DESIGN.md` section 9 for the cost line and `infra/README.md` "DNSSEC" / "DNS query logs" for verification (`task dns-check`) and the rollback order.
