# 0006. Kubernetes and Kafka are part of the bank

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D6

## Context

Most banks run a Prometheus-monitored Kubernetes estate next to newer serverless services, glued by Kafka. A triage system that has never seen an Alertmanager webhook or a consumer-lag alert is not credible.

## Decision

The Kubernetes estate runs three services, kube-prometheus-stack and Strimzi Kafka (KRaft, one broker). Kafka is both the business event backbone (card.authorized, fraud.scored) and an alert transport (alerts.raw).

## Consequences

Two alert routes exist by necessity: over Kafka (route A) and over HTTPS (route B) for the alerts that cannot travel over Kafka, such as KafkaBrokerDown. Where the estate runs is ADR 0007.
