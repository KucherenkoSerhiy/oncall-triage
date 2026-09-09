# 0005. AWS eu-north-1 (Stockholm) and Azure westeurope

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D5

## Context

A European bank narrative implies EU data residency; both regions carry every service used.

## Decision

eu-north-1 (Stockholm) for AWS, westeurope for Azure. Route 53, CloudFront and ACM-for-CloudFront (us-east-1) are global and unaffected. Amended 2026-09-09: originally eu-central-1; the AWS account was created through the new sign-up experience and carries an AWS-managed region-floor service control policy that allows eu-north-1 plus global services. Moving the home region keeps that guardrail intact instead of editing an AWS-managed policy (see ADR 0014).

## Consequences

Cross-region latency between the estates is a few tens of milliseconds and irrelevant to alert triage.
