# 0005. AWS eu-north-1 (Stockholm) and Azure northeurope (Ireland)

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D5

## Context

A European bank narrative implies EU data residency; both regions carry every service used.

## Decision

eu-north-1 (Stockholm) for AWS, westeurope for Azure. Route 53, CloudFront and ACM-for-CloudFront (us-east-1) are global and unaffected. Amended 2026-09-09: originally eu-central-1; the AWS account was created through the new sign-up experience and carries an AWS-managed region-floor service control policy that allows eu-north-1 plus global services. Moving the home region keeps that guardrail intact instead of editing an AWS-managed policy (see ADR 0014).

## Consequences

Cross-region latency between the estates is a few tens of milliseconds and irrelevant to alert triage.

## Amendment 2026-09-10 - Azure workloads move to northeurope

The first `infra/azure` apply (M5b) failed on every regional resource with
`RequestDisallowedByAzure: The selected region is currently not accepting new
customers` for westeurope - a capacity restriction Azure applies to newer
subscriptions in its most popular regions. The resource group created by the
bootstrap stays in westeurope (a resource group's location is only metadata
for its own record); every workload resource takes `var.location`, default
`northeurope`, which accepted a test storage account (as did swedencentral).
northeurope is chosen over swedencentral for feature completeness on the
Consumption plan and Azure Monitor. Data residency stays in the EU.
