# `nordwind-bank` Helm chart

Deploys the three Kubernetes bank services (`bank/k8s/cards_authorization`,
`bank/k8s/fraud_scoring`, `bank/k8s/open_banking_api`) as one Deployment +
Service + ServiceMonitor each, a shared fault-injection ConfigMap, and (when
`kafka.enabled`, the default) Strimzi Kafka plus `alerts-bridge` and
`kafka-relay` (M7b, route A) each as their own Deployment + Service +
ServiceMonitor - see "Kafka" below. One `PrometheusRule` carries the alert
rules that make the estate's chaos scenarios observable. M6a ships the chart
and its offline gates (`helm lint`, `helm template | kubeconform`, `trivy
config`); M6b (kind, `task estate-up`, `estate-demo.yml`) is what actually
installs it onto a live cluster.

## Values

| Value | Default | Purpose |
| --- | --- | --- |
| `imageTag` | `latest` | Tag applied to `nordwind/<service>:<imageTag>`. `imagePullPolicy: IfNotPresent` so `kind load docker-image` works without a registry. |
| `forwarder.url` | `""` | Not read by this chart directly - kept here so `--set forwarder.url=...` is the one flag M6b needs for the whole estate. The value that actually matters lives in `deploy/helm/values/kube-prometheus-stack.yaml`'s Alertmanager config, substituted by `scripts/render_alertmanager_values.py`. |
| `kafka.enabled` | `true` | Renders `templates/kafka/` (Strimzi `Kafka` + `KafkaNodePool`, `KafkaTopic`s, `KafkaUser`s, the JMX metrics `ConfigMap`, the `PodMonitor`, and the `alerts-bridge`/`kafka-relay` Deployments) and the Kafka env/volumes on the three service Deployments. `--set kafka.enabled=false` renders the M6 estate with none of that - both are gated in CI (`task helm-check`, `ci.yml`'s `helm` job). |
| `kafkaRelay.ingestUrl` | the production ingest URL | Where `kafka-relay` POSTs route-A alerts (M7b). `INGEST_HMAC_SECRET` is not a value - see "Kafka" below. |
| `monitoring.release` | `monitoring` | Stamped as the `release` label on the `ServiceMonitor`/`PrometheusRule` objects (see "How Prometheus finds these objects" below). Must match the Helm release name kube-prometheus-stack is installed under. |
| `services` | the three service names | List of `{name}` objects the Deployment/Service/ServiceMonitor templates range over. Not meant to be overridden - a fourth k8s bank service is a chart change, not a values change; `alerts-bridge`/`kafka-relay` are not in this list (they need Kafka to exist first) - see `templates/kafka/`. |

## How faults reach pods

One ConfigMap, `nordwind-faults`, with one key per service
(`cards-authorization`, `fraud-scoring`, `open-banking-api`), each key
empty by default. Each service's Deployment mounts the ConfigMap at
`/etc/nordwind` but projects only **its own** key, via `items` +
`path: fault`:

```yaml
volumes:
  - name: faults
    configMap:
      name: nordwind-faults
      items:
        - key: cards-authorization
          path: fault
```

So every pod always reads the same path, `/etc/nordwind/fault`, but each
service's Deployment wires it to a different ConfigMap key. `bankops chaos
--estate kubernetes` (M6b) patches the relevant key; `bank/k8s/_shared/faults.py`
re-reads the mounted file at most once every 5 seconds.

## How Prometheus finds these objects

`deploy/helm/values/kube-prometheus-stack.yaml` sets
`serviceMonitorSelectorNilUsesHelmValues: false` and
`ruleSelectorNilUsesHelmValues: false`, which makes kube-prometheus-stack's
Prometheus select **every** ServiceMonitor/PrometheusRule cluster-wide
(the nil selector, used as-is, matches everything) rather than only ones
labelled with its own release name. That's the primary mechanism this
chart relies on. The `release: {{ .Values.monitoring.release }}` label on
the `ServiceMonitor` and `PrometheusRule` objects is kept anyway, as a
second, redundant path: if the upstream values ever revert those two
flags to their (more restrictive) defaults, kube-prometheus-stack's
default selector behaviour is to require exactly that label, and these
objects would still be picked up with no chart change needed.

## How rules map to services and severities

Group `nordwind-bank.rules`, each labelled `severity` (and `service`, except
`KafkaConsumerLag` - see below) and annotated `summary` + `description`:

| Alert | Service | Severity | Fires when |
| --- | --- | --- | --- |
| `CardsAuthHighLatency` | cards-authorization | high | p99 of `cards_auth_request_seconds` > 1s for 2m |
| `CardsAuthErrorRatio` | cards-authorization | critical | `result="error"` ratio > 50% for 2m |
| `FraudScoreDrift` | fraud-scoring | high | mean `fraud_score_bucket` observation > 0.6 for 3m |
| `FraudScoringCrashLoop` | fraud-scoring | high | container restarts increase by > 2 over 10m |
| `OpenBankingRateLimitStorm` | open-banking-api | warning | `code="429"` ratio > 50% for 2m |
| `OpenBankingCertExpiringSoon` | open-banking-api | warning | `openbanking_cert_expiry_seconds` < 14 days away |
| `KafkaBrokerDown` (M7b, `kafka.enabled`) | kafka | critical | `kafka_server_replicamanager_leadercount` absent, or every `up{job=~".*kafka.*"}` target down, for 1m |
| `KafkaConsumerLag` (M7b, `kafka.enabled`) | *dynamic* - the `consumergroup` label, via `label_replace` | high | `sum by (consumergroup) (kafka_consumergroup_lag)` > 50 for 2m |
| `KafkaRelayLag` (M7b, `kafka.enabled`) | kafka-relay | high | `kafka_consumergroup_lag{consumergroup="kafka-relay"}` > 20 for 2m, or no successful post in 300s |
| `AlertsBridgeDown` (M7b, `kafka.enabled`) | alerts-bridge | critical | `up{job=~".*alerts-bridge.*"} == 0` for 1m |
| `KafkaRelayDown` (M7b, `kafka.enabled`) | kafka-relay | critical | `up{job=~".*kafka-relay.*"} == 0` for 1m |

`for` durations are short on purpose - M6b's chaos scenarios need to reach
a verdict in a handful of minutes, not hours. The four Kafka-alert names
above (not `KafkaConsumerLag`) are exactly the set
`deploy/helm/values/kube-prometheus-stack.yaml` routes to route B instead of
route A - see that file and ADR 0015.

## Kafka (M7a)

`templates/kafka/` (behind `kafka.enabled`) renders a Strimzi (KRaft) Kafka
cluster named after the Helm release (so the bootstrap Service is
`<release>-kafka-bootstrap.bank.svc:9093` and the cluster CA cert Secret is
`<release>-cluster-ca-cert`):

- Two `KafkaNodePool`s, not one combined `dual-role` pool: `controller` (1
  replica, ephemeral storage, 512 Mi, never touched) and `broker` (1 replica,
  ephemeral storage, 1 Gi). `broker-down` (`scripts/chaos_k8s.py`) pauses
  the operator's reconciliation and deletes the broker's StrimziPodSet - a
  broker pool cannot be scaled to 0 in KRaft mode (#78) - so keeping the
  controller in its own pool means the metadata quorum survives the outage
  and recovery is a plain resume.
- `Kafka` - listener `tls` on 9093 with `scram-sha-512`,
  `authorization.type: simple` (`admin` is the sole `superUser`),
  `metricsConfig` pointing at the `kafka-metrics` ConfigMap (the Strimzi
  example JMX exporter rules, trimmed to broker + topic metrics), and
  `kafkaExporter` enabled (`groupRegex`/`topicRegex: ".*"` - this is what
  exports `kafka_consumergroup_lag`).
- `KafkaTopic`s `card.authorized`, `fraud.scored`, `alerts.raw` - 1
  partition, 1 replica, 24h retention.
- A `PodMonitor` selecting `strimzi.io/cluster: <release>` so Prometheus
  scrapes both the broker JMX metrics and kafka-exporter.

### Users and ACLs

Each `KafkaUser` gets `scram-sha-512` authentication and a `simple`
authorization block scoped to exactly what that client does - Strimzi
generates a Secret named after the user, containing the SCRAM `password`:

| User | ACLs |
| --- | --- |
| `cards-authorization` | Write, Describe on `card.authorized` |
| `fraud-scoring` | Read, Describe on `card.authorized`; Write, Describe on `fraud.scored`; Read on group `fraud-scoring` |
| `open-banking-api` | Read, Describe on `fraud.scored`; Read on group `open-banking-api` |
| `alerts-bridge` | Write, Describe on `alerts.raw` |
| `kafka-relay` | Read, Describe on `alerts.raw`; Read on group `kafka-relay` |
| `admin` | none - a Kafka-level `superUser`, used only by `scripts/estate_status.py --kafka` to run `kafka-consumer-groups.sh --describe --all-groups` |

All five service Deployments (the three M7a business services plus M7b's
`alerts-bridge`/`kafka-relay`) mount their own user Secret and the cluster CA
cert Secret, and get `KAFKA_BOOTSTRAP`, `KAFKA_USER`, `KAFKA_PASSWORD_FILE`
(`/etc/nordwind/kafka/user/password`), `KAFKA_CA_FILE`
(`/etc/nordwind/kafka/ca/ca.crt`) - see `bank/k8s/_shared/kafka.py`'s
`KafkaSettings.from_env()`. With `kafka.enabled=false` none of that is
rendered: the three business services fall back to M6 ticker-only behaviour,
and `alerts-bridge`/`kafka-relay` don't render at all.

## alerts-bridge and kafka-relay (M7b, route A)

`templates/kafka/alerts-bridge.yaml` and `templates/kafka/kafka-relay.yaml`
(also behind `kafka.enabled`) render one Deployment + Service + ServiceMonitor
each, outside the generic `.Values.services` loop above - the fault
ConfigMap doesn't apply to them, and they only exist with Kafka.

- **alerts-bridge**'s Service is named `<release>-alerts-bridge`
  (release-prefixed, unlike the three services above): the Alertmanager
  webhook URL in `deploy/helm/values/kube-prometheus-stack.yaml` is a plain
  values file for a *different* Helm release and can't read this chart's
  `.Release.Name`, so it hardcodes `nordwind-bank-alerts-bridge.bank.svc` -
  matching only as long as this chart installs under the release name
  `nordwind-bank` (`Taskfile.yml`'s `estate-up` always does).
- **kafka-relay** additionally gets `INGEST_URL` (`values.yaml`'s
  `kafkaRelay.ingestUrl`) and `INGEST_HMAC_SECRET`, sourced via
  `secretKeyRef` from a Secret named `nordwind-ingest`, key `hmac-secret` -
  this chart references that Secret **by name only**, never its value.
  `task estate-up` creates it from an SSM parameter before installing this
  chart; see `docs/runbooks/kubernetes-estate.md`.

### Tailing a topic

```bash
BROKER_POD=$(kubectl -n bank get pod -l strimzi.io/pool-name=broker -o jsonpath='{.items[0].metadata.name}')
PASSWORD=$(kubectl -n bank get secret cards-authorization -o jsonpath='{.data.password}' | base64 -d)
CA_PASSWORD=$(kubectl -n bank get secret nordwind-bank-cluster-ca-cert -o jsonpath='{.data.ca\.password}' | base64 -d)
kubectl -n bank exec "$BROKER_POD" -- sh -c "
  cat > /tmp/client.properties <<'EOF'
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username=\"cards-authorization\" password=\"$PASSWORD\";
ssl.truststore.location=/opt/kafka/cluster-ca-certs/ca.p12
ssl.truststore.password=$CA_PASSWORD
ssl.truststore.type=PKCS12
ssl.endpoint.identification.algorithm=
EOF
  bin/kafka-console-consumer.sh --bootstrap-server localhost:9093 \
    --consumer.config /tmp/client.properties --topic card.authorized --from-beginning"
```

## What M6b adds

Everything that needs a live cluster: `deploy/kind/cluster.yaml`, the
`task estate-up` / `estate-down` / `estate-status` / `chaos-k8s` Taskfile
targets (including running `scripts/render_alertmanager_values.py` and
`helm upgrade --install`), `.github/workflows/estate-demo.yml`, and
`docs/runbooks/kubernetes-estate.md`.

## What M7b adds

`alerts-bridge` and `kafka-relay` (above), the `route-a-kafka` /
`route-b-forwarder` Alertmanager routing and its five extra `PrometheusRule`
alerts, the `nordwind-ingest` Secret creation step in `task estate-up`, and
the `fraud-lag` / `broker-down` chaos scenarios
(`scripts/estate_scenarios.py`). See ADR 0015 for why the estate needs a
relay at all rather than a Kafka endpoint AWS can reach directly.
