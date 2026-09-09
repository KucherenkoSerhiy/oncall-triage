# 0005. AWS eu-north-1 (Stockholm) and Azure swedencentral (Stockholm)

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D5

## Context

A European bank narrative implies EU data residency; both regions carry every service used.

## Decision

eu-north-1 (Stockholm) for AWS, westeurope for Azure. Route 53, CloudFront and ACM-for-CloudFront (us-east-1) are global and unaffected. Amended 2026-09-09: originally eu-central-1; the AWS account was created through the new sign-up experience and carries an AWS-managed region-floor service control policy that allows eu-north-1 plus global services. Moving the home region keeps that guardrail intact instead of editing an AWS-managed policy (see ADR 0014).

## Consequences

Cross-region latency between the estates is a few tens of milliseconds and irrelevant to alert triage.

## Amendment 2026-09-10 - Azure workloads move out of westeurope

The first `infra/azure` apply (M5b) failed on every regional resource with
`RequestDisallowedByAzure: The selected region is currently not accepting new
customers` for westeurope - a capacity restriction Azure applies to newer
subscriptions in its most popular regions. The resource group created by the
bootstrap stays in westeurope (a resource group's location is only metadata
for its own record); every workload resource takes `var.location`. northeurope was the first
choice (it accepted a test storage account) but the next apply failed on the
Consumption plan with `Operation cannot be completed without additional
quota - Current Limit (Y1 VMs): 0`. A raw ARM probe of a Y1 Linux plan per
region gave: swedencentral OK, francecentral OK, northeurope / uksouth /
germanywestcentral quota 0, westeurope forbidden. Default is therefore
**swedencentral** - Stockholm, the same city as the AWS spine, so the
"EU bank, one metro, two clouds" narrative holds. Data residency stays in
the EU. If a region's quota changes, `-var=location=...` moves the estate
(all resources are regional and recreate; nothing is stateful yet).
