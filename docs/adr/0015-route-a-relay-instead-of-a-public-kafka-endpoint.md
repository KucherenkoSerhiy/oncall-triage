# 0015. Route A relay instead of a public Kafka endpoint

- Status: accepted
- Date: 2026-09-10
- Design reference: docs/DESIGN.md, decision D7; docs/DESIGN.md §4.4

## Context

Kafka (Strimzi, KRaft) runs inside the `kind` cluster as the Kubernetes estate's event backbone and, from M7, its alert transport: Prometheus rules fire, Alertmanager should be able to deliver those alerts as Kafka messages rather than only over HTTPS. But `kind` has no public endpoint - it's a laptop or a GitHub Actions runner, with no stable address and no ingress the AWS triage brain could dial into, and giving it one would mean a cloud-managed cluster with a load balancer or NodePort exposed to the internet, plus a TLS listener and a network path the brain trusts.

Two ways to get a real cluster with a reachable Kafka were considered instead of solving this inside `kind`:

- **AKS with Azure Private Link** (or an AKS Kafka endpoint reachable from AWS over a VPN/peering): a managed control plane (~$73/month minimum for the free tier's node pool alone) plus a Private Link/VNet gateway resource - real money for what this milestone needs to demonstrate, and out of the ≤$10/month budget (D1, DESIGN.md §1).
- **Amazon MSK**: the smallest MSK Serverless or provisioned cluster starts in the tens of dollars per month and needs its own VPC wiring; same budget problem, and it would mean the "Kubernetes Kafka" the estate demonstrates isn't actually the one AWS talks to.

Both give AWS a direct line to Kafka, but at a cost this portfolio project's budget doesn't allow (non-requirement in every M7 spec slice: "nothing here costs money").

## Decision

Keep Kafka entirely inside the cluster and add a relay: `alerts-bridge` (an Alertmanager webhook receiver) produces each firing alert to the `alerts.raw` topic, and `kafka-relay` consumes it, HMAC-signs it the same way every other estate signs its ingest webhook, and POSTs it out over plain outbound HTTPS - the one kind of connection that works unmodified from a laptop, a GitHub Actions runner, or any other `kind` host. Alertmanager still defaults every alert to this route ("route A"); the four alerts *about* Kafka itself (`KafkaBrokerDown`, `KafkaRelayLag`, `AlertsBridgeDown`, `KafkaRelayDown`) take a second, pre-existing path ("route B", the `bank/azure/alert_forwarder` webhook) instead, since an alert reporting Kafka broken cannot reliably travel over Kafka to say so.

## Consequences

`kafka-relay` is the one component inside the cluster that holds the ingest HMAC secret (mounted from the `nordwind-ingest` Kubernetes Secret, itself created from the same SSM parameter every other estate's ingest secret comes from) - a single, well-scoped place to reason about that credential's blast radius, rather than every Kafka client needing outbound network trust. The `broker-down` chaos scenario is the visible proof this design is honest: scale the broker to zero, and the alert that shows up on the console is the one that traveled route B, not route A - the system cannot claim its Kafka alert transport survived a Kafka outage. If a future milestone wants AWS to consume the estate's Kafka directly (real cross-cloud event streaming, not just alert delivery), that's the AKS/MSK option revisited with its own budget line, not a change to this relay.
