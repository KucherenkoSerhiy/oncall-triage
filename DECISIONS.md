# Implementation decisions (M7a)

The M7a spec (`docs/specs/m7a-strimzi-kafka-wiring.md`) is detailed but
leaves some concrete choices open. Recorded here rather than guessed
silently.

- **Strimzi operator version: 0.45.0, Kafka version 3.9.0.** The spec calls
  for "KRaft annotations" (`strimzi.io/kraft`, `strimzi.io/node-pools`),
  which are required through Strimzi 0.47.x and become no-op (ignored) from
  0.48.0 on - so a version in that range keeps the annotations meaningful.
  0.45.0 is the last version before ZooKeeper support was dropped (0.46.0)
  and supports Kafka 3.9.0/3.8.1. `metadataVersion: 3.9-IV0` follows the
  Kafka version. Confirmed against the real
  `strimzi-kafka-operator` Helm chart's `values.yaml` at that tag (`watchNamespaces`,
  `watchAnyNamespace`, `resources`) and the real CRD schemas (datreeio
  CRDs-catalog, commit `ad3b08c5045129d7bb1eeffd8e61719b2c8dd1e2`) - `helm
  template | kubeconform -strict` passes against them.
- **Kafka resource naming.** The Kafka resource is named
  `{{ .Release.Name }}` (not `<release>-kafka`) so that Strimzi's generated
  bootstrap Service, `<clusterName>-kafka-bootstrap`, matches the spec's
  literal `<release>-kafka-bootstrap.bank.svc:9093`. KafkaNodePool names are
  fixed literals (not release-templated) since `scripts/chaos_k8s.py`/
  `estate_status.py` need a name to patch/exec against without discovering
  the release name first.
- **Two KafkaNodePools instead of one `dual-role` pool.** The spec calls
  for a single `dual-role` (`controller` + `broker`) pool, but live-testing
  against a real Strimzi cluster showed the `broker-down` chaos action
  (scale a KafkaNodePool to 0) can't work against it: Strimzi's cluster
  operator refuses to reconcile a Kafka cluster whose node pools sum to 0
  replicas across the board, so scaling the one combined pool to 0 just
  loops reconcile errors and leaves the existing broker pod running - a
  silent no-op fault. Split into `controller` (1 replica, never touched)
  and `broker` (1 replica, what `broker-down` scales to 0) so the fault
  actually removes the broker while the KRaft metadata quorum stays up.
  Deviates from the spec's literal "`dual-role`, 1 replica" pool in order
  to make the `broker-down` requirement (which the same spec sentence
  requires) actually work.
- **kafka-metrics ConfigMap trim.** "Trimmed to broker + topic metrics"
  means the Strimzi example `kafka-metrics-config.yml`'s generic
  `kafka.server`/`BrokerTopicMetrics`-shaped rules (which already carry a
  `topic` label via the first "special case" pattern), with the
  KRaft-internals-only sections (`raft-metrics`, `raft-channel-metrics`,
  `broker-metadata-metrics`) dropped - those are Raft consensus internals,
  not broker or topic throughput/latency metrics.
- **Event payload shapes.** `card.authorized`:
  `{"txn_id", "amount", "currency": "EUR", "result", "ts"}` - `txn_id` a
  UUID4, `amount` a random 1.00-500.00 (matching the synthetic-latency style
  already used for the service's other random values), `ts` epoch seconds.
  `fraud.scored`: `{"txn_id", "score", "ts"}`, produced by fraud-scoring's
  consumer handler using the exact scoring distribution `work()` already
  used (`_score()`, extracted so both paths share it).
- **`ConsumerLoop`'s handler owns committing.** `handle_message(consumer,
  message)` (not just `handle_message(message)`) so fraud-scoring can commit
  only after a successful publish to `fraud.scored`, while open-banking-api
  commits right after counting - two different commit policies sharing one
  loop implementation.
- **Redpanda contract tests: real `confluent_kafka` clients, not
  `KafkaSettings`.** The contract tests build plain `bootstrap.servers`-only
  producers/consumers (via `_shared.kafka.KafkaPublisher`/`ConsumerLoop`
  directly) rather than exercising `KafkaSettings.client_config()`'s
  SASL_SSL/SCRAM path, since Redpanda's testcontainers image isn't
  configured with SCRAM/TLS - `security.protocol=SASL_SSL` +
  `ssl.ca.location` are unit-tested against `KafkaSettings` directly instead
  (`tests/bank/k8s/test_kafka.py`). Redpanda image pinned to
  `redpandadata/redpanda:v25.3.17`. Each contract test builds a group-lag
  comparison via `confluent_kafka.admin.AdminClient.list_consumer_group_offsets`
  + a throwaway consumer's `get_watermark_offsets`, since the spec allows
  "Redpanda's admin API (or `rpk`)" for that.
- **`estate_status.py --kafka`'s admin client wiring.** The `admin` user's
  password comes from its generated Secret; the truststore is the cluster
  CA cert Secret's `ca.p12` (mounted into the broker pod's own filesystem at
  the Strimzi-conventional `/opt/kafka/cluster-ca-certs/ca.p12`, with the
  store password at the `ca.password` key of the same Secret,
  `<release>-cluster-ca-cert`) - built into a throwaway
  `/tmp/admin.properties` inside the broker pod via `kubectl exec ... sh -c`.
  `ssl.endpoint.identification.algorithm=` (empty) is required in that
  properties file: connecting to `localhost:9093` from inside the broker
  pod otherwise fails TLS hostname verification, since the broker's
  certificate SAN doesn't cover "localhost" - found and fixed after
  live-testing against a real cluster.
- **`task estate-up` namespace ordering.** The Strimzi operator chart's
  `watchNamespaces: [bank]` value makes it create RoleBindings in `bank` at
  install time, so `bank` must exist before installing
  `strimzi-kafka-operator`, not just before `nordwind-bank` (which creates
  it via `--create-namespace`) later - found live-testing on a fresh kind
  cluster. `task estate-up` now runs a `kubectl create namespace bank`
  (idempotent, dry-run/apply) ahead of the Strimzi install.
