# Generated C4 diagrams

Exported from [`../workspace.dsl`](../workspace.dsl) by `task c4`; do not edit by hand.

## Level 1 — system context

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["System Context View: Alert Triage"]
    style diagram fill:#ffffff,stroke:#ffffff

    1["<div style='font-weight: bold'>On-call engineer</div><div style='font-size: 70%; margin-top: 0px'>[Person]</div><div style='font-size: 80%; margin-top:10px'>Reads verdicts on the<br />incident console and teaches<br />known issues.</div>"]
    style 1 fill:#0f766e,stroke:#0a524d,color:#ffffff
    25["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 25 fill:#1c2530,stroke:#131921,color:#ffffff
    3["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
    style 3 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    32["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 32 fill:#1c2530,stroke:#131921,color:#ffffff
    37["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 37 fill:#1c2530,stroke:#131921,color:#ffffff
    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff

    37-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5
    37-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->32
    5-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3
    5-. "<div>e-mail notification</div><div style='font-size: 70%'></div>" .->1
    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->25
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->32
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->37
    25-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->5
    5-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->25
    32-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5

  end
```

## Level 2 — the triage brain and its inbound sources

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Container View: Alert Triage"]
    style diagram fill:#ffffff,stroke:#ffffff

    1["<div style='font-weight: bold'>On-call engineer</div><div style='font-size: 70%; margin-top: 0px'>[Person]</div><div style='font-size: 80%; margin-top:10px'>Reads verdicts on the<br />incident console and teaches<br />known issues.</div>"]
    style 1 fill:#0f766e,stroke:#0a524d,color:#ffffff
    3["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
    style 3 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    25["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 25 fill:#1c2530,stroke:#131921,color:#ffffff
    32["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 32 fill:#1c2530,stroke:#131921,color:#ffffff
    37["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 37 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      15[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
      style 15 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      16["<div style='font-weight: bold'>console API</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda + API Gateway HTTP API]</div><div style='font-size: 80%; margin-top:10px'>Reads alerts and verdicts;<br />accepts taught known issues.<br />Bearer-token protected (v1).</div>"]
      style 16 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      17["<div style='font-weight: bold'>incident console</div><div style='font-size: 70%; margin-top: 0px'>[Container: Static site on S3 + CloudFront at triage.serhiykucherenko.dev]</div><div style='font-size: 80%; margin-top:10px'>Live alert list, verdicts,<br />known-issues editor.</div>"]
      style 17 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      18["<div style='font-weight: bold'>secrets</div><div style='font-size: 70%; margin-top: 0px'>[Container: SSM Parameter Store (SecureString)]</div><div style='font-size: 80%; margin-top:10px'>Anthropic key and webhook<br />HMAC secret.</div>"]
      style 18 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      19["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p95, DLQ depth, SLO<br />attainment; five ops alarms.</div>"]
      style 19 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      20["<div style='font-weight: bold'>ops topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>Human-only: CloudWatch alarm<br />state changes for the triage<br />brain itself, never fed back<br />into ingest.</div>"]
      style 20 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      21["<div style='font-weight: bold'>slo-reporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Daily (00:15 UTC): reads<br />yesterday's triaged alerts<br />and verdicts, computes<br />latency p95 and SLO<br />attainment.</div>"]
      style 21 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      22["<div style='font-weight: bold'>dns</div><div style='font-size: 70%; margin-top: 0px'>[Container: Route 53 hosted zone]</div><div style='font-size: 80%; margin-top:10px'>DNSSEC-signed; query logs</div>"]
      style 22 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      23[("<div style='font-weight: bold'>known-issues bucket</div><div style='font-size: 70%; margin-top: 0px'>[Container: S3]</div><div style='font-size: 80%; margin-top:10px'>Weekly JSON export of taught<br />known issues, so the memory<br />survives a table wipe;<br />expires after 30 days.</div>")]
      style 23 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      24["<div style='font-weight: bold'>known-issues-export</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Weekly (Monday 00:30 UTC):<br />scans the known-issues table<br />and writes a dated JSON<br />export to the bucket.</div>"]
      style 24 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      7["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
      style 7 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      8["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
      style 8 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    37-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->6
    37-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->32
    6-. "<div>put alert</div><div style='font-size: 70%'></div>" .->15
    6-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->7
    7-. "<div>triggers</div><div style='font-size: 70%'></div>" .->8
    8-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->15
    8-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->18
    8-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->19
    8-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3
    17-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    16-. "<div>query / put</div><div style='font-size: 70%'></div>" .->15
    21-. "<div>reads yesterday</div><div style='font-size: 70%'></div>" .->15
    21-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->19
    24-. "<div>scans known issues</div><div style='font-size: 70%'></div>" .->15
    24-. "<div>put known-issues-<date>.json</div><div style='font-size: 70%'></div>" .->23
    6-. "<div>alarm state change<br />(IngestErrorRatio)</div><div style='font-size: 70%'></div>" .->20
    8-. "<div>alarm state change<br />(WorkerErrors,<br />WorkerDurationP95,<br />CapReached)</div><div style='font-size: 70%'></div>" .->20
    7-. "<div>alarm state change<br />(AlertsDlqDepth)</div><div style='font-size: 70%'></div>" .->20
    20-. "<div>e-mail notification</div><div style='font-size: 70%'></div>" .->1
    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->17
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->25
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->32
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->37
    25-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->6
    16-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->25
    32-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    32-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6

  end
```

## Level 2 — the Kubernetes estate: services, Kafka, bridge, relay, Alertmanager

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Container View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff
    32["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 32 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 37 ["Nordwind Kubernetes estate (kind)"]
      style 37 fill:#ffffff,stroke:#131921,color:#131921

      38["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
      style 38 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      39["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
      style 39 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      40["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
      style 40 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      41["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      42["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
      style 42 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      43["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
      style 43 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      44["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
      style 44 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      45["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 45 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      46["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 46 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    46-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->32
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->32
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->38
    32-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    45-. "<div>scrape</div><div style='font-size: 70%'></div>" .->38
    45-. "<div>scrape</div><div style='font-size: 70%'></div>" .->39
    45-. "<div>scrape</div><div style='font-size: 70%'></div>" .->40
    45-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->41
    45-. "<div>scrape</div><div style='font-size: 70%'></div>" .->42
    45-. "<div>scrape</div><div style='font-size: 70%'></div>" .->43
    45-. "<div>scrape</div><div style='font-size: 70%'></div>" .->44
    45-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->46
    38-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->41
    39-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->41
    40-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->41
    42-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->41
    46-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->43
    43-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->41
    44-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->41
    44-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5

  end
```

## Dynamic — an alert travels over Kafka (route A)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Dynamic View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 37 ["Nordwind Kubernetes estate (kind)"]
      style 37 fill:#ffffff,stroke:#131921,color:#131921

      41["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      43["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
      style 43 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      44["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
      style 44 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      45["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 45 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      46["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 46 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    45-. "<div>1. rule fires</div><div style='font-size: 70%'></div>" .->46
    46-. "<div>2. route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->43
    43-. "<div>3. produce alerts.raw</div><div style='font-size: 70%'></div>" .->41
    44-. "<div>4. consume alerts.raw</div><div style='font-size: 70%'></div>" .->41
    44-. "<div>5. HTTPS + HMAC</div><div style='font-size: 70%'></div>" .->6

  end
```

## Dynamic — the alert about Kafka takes route B

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Dynamic View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 32 ["Nordwind serverless estate (Azure)"]
      style 32 fill:#ffffff,stroke:#131921,color:#131921

      36["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
      style 36 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 37 ["Nordwind Kubernetes estate (kind)"]
      style 37 fill:#ffffff,stroke:#131921,color:#131921

      45["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 45 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      46["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 46 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    45-. "<div>1. KafkaBrokerDown fires</div><div style='font-size: 70%'></div>" .->46
    46-. "<div>2. route B webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->36
    36-. "<div>3. HTTPS + HMAC</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6

  end
```

## Level 3 — inside the triage worker

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Component View: Alert Triage - triage worker"]
    style diagram fill:#ffffff,stroke:#ffffff

    3["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
    style 3 fill:#8fa1b0,stroke:#64707b,color:#ffffff

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      subgraph 8 ["triage worker"]
        style 8 fill:#ffffff,stroke:#0e8074,color:#0e8074

        10["<div style='font-weight: bold'>researcher</div><div style='font-size: 70%; margin-top: 0px'>[Component: ADK Agent]</div><div style='font-size: 80%; margin-top:10px'>Characterises a genuinely new<br />error from its text alone:<br />cause category, severity,<br />next step. Deliberately<br />tool-less.</div>"]
        style 10 fill:#99f6e4,stroke:#6bac9f,color:#0e1419
        11["<div style='font-weight: bold'>reporter</div><div style='font-size: 70%; margin-top: 0px'>[Component: ADK Agent]</div><div style='font-size: 80%; margin-top:10px'>Produces the final text in<br />exactly one of two formats<br />plus a machine-readable<br />verdict block.</div>"]
        style 11 fill:#99f6e4,stroke:#6bac9f,color:#0e1419
        12["<div style='font-weight: bold'>tools</div><div style='font-size: 70%; margin-top: 0px'>[Component: Python functions]</div><div style='font-size: 80%; margin-top:10px'>get_alert, get_recent_alerts,<br />check_known, remember_issue</div>"]
        style 12 fill:#99f6e4,stroke:#6bac9f,color:#0e1419
        13["<div style='font-weight: bold'>KnownIssueStore</div><div style='font-size: 70%; margin-top: 0px'>[Component: Python interface + adapters]</div><div style='font-size: 80%; margin-top:10px'>JsonFileStore for tests and<br />local runs, DynamoStore in<br />the cloud.</div>"]
        style 13 fill:#99f6e4,stroke:#6bac9f,color:#0e1419
        14["<div style='font-weight: bold'>LiteLlm model adapter</div><div style='font-size: 70%; margin-top: 0px'>[Component: google.adk.models.lite_llm]</div><div style='font-size: 80%; margin-top:10px'>anthropic/claude-haiku-4-5</div>"]
        style 14 fill:#99f6e4,stroke:#6bac9f,color:#0e1419
        9["<div style='font-weight: bold'>triage agent</div><div style='font-size: 70%; margin-top: 0px'>[Component: ADK Agent]</div><div style='font-size: 80%; margin-top:10px'>Root agent: pulls alert<br />context, checks the<br />known-issues store, decides<br />the hand-off.</div>"]
        style 9 fill:#99f6e4,stroke:#6bac9f,color:#0e1419
      end

      15[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
      style 15 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    9-. "<div>get_alert, get_recent_alerts,<br />check_known, remember_issue</div><div style='font-size: 70%'></div>" .->12
    9-. "<div>transfer: new error</div><div style='font-size: 70%'></div>" .->10
    9-. "<div>transfer: known or<br />characterised error</div><div style='font-size: 70%'></div>" .->11
    10-. "<div>characterisation, via the<br />root agent</div><div style='font-size: 70%'></div>" .->11
    12-. "<div>find_known / add_known</div><div style='font-size: 70%'></div>" .->13
    13-. "<div>DynamoStore reads/writes</div><div style='font-size: 70%'></div>" .->15
    12-. "<div>get_alert / get_recent_alerts</div><div style='font-size: 70%'></div>" .->15
    9-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14
    10-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14
    11-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14
    14-. "<div>HTTPS</div><div style='font-size: 70%'></div>" .->3

  end
```

## Deployment — where every container runs in `demo` (AWS, Azure)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: demo"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 136 ["AWS"]
      style 136 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 137 ["Lambda"]
        style 137 fill:#ffffff,stroke:#444444,color:#444444

        138["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
        style 138 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        139["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
        style 139 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        140["<div style='font-weight: bold'>payments</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Card payment authorisation<br />API. Chaos: errors, latency,<br />pool.</div>"]
        style 140 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        141["<div style='font-weight: bold'>ledger</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Double-entry posting worker<br />fed by SQS. Chaos:<br />reconciliation-mismatch, lag.</div>"]
        style 141 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        142["<div style='font-weight: bold'>auth</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Token issuance / JWKS. Chaos:<br />jwks-rotation, lockouts.</div>"]
        style 142 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        143["<div style='font-weight: bold'>slo-reporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Daily (00:15 UTC): reads<br />yesterday's triaged alerts<br />and verdicts, computes<br />latency p95 and SLO<br />attainment.</div>"]
        style 143 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        144["<div style='font-weight: bold'>known-issues-export</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Weekly (Monday 00:30 UTC):<br />scans the known-issues table<br />and writes a dated JSON<br />export to the bucket.</div>"]
        style 144 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 145 ["API Gateway"]
        style 145 fill:#ffffff,stroke:#444444,color:#444444

        146["<div style='font-weight: bold'>console API</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda + API Gateway HTTP API]</div><div style='font-size: 80%; margin-top:10px'>Reads alerts and verdicts;<br />accepts taught known issues.<br />Bearer-token protected (v1).</div>"]
        style 146 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 147 ["SQS"]
        style 147 fill:#ffffff,stroke:#444444,color:#444444

        148["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
        style 148 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        151["<div style='font-weight: bold'>ledger queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples payments from<br />ledger posting; DLQ after 5<br />failed attempts.</div>"]
        style 151 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 154 ["SNS"]
        style 154 fill:#ffffff,stroke:#444444,color:#444444

        155["<div style='font-weight: bold'>alarm topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>CloudWatch alarm state<br />changes fan out here.</div>"]
        style 155 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        160["<div style='font-weight: bold'>ops topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>Human-only: CloudWatch alarm<br />state changes for the triage<br />brain itself, never fed back<br />into ingest.</div>"]
        style 160 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 164 ["DynamoDB"]
        style 164 fill:#ffffff,stroke:#444444,color:#444444

        165[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
        style 165 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        171[("<div style='font-weight: bold'>faults</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB]</div><div style='font-size: 80%; margin-top:10px'>One fault flag per service,<br />set by bankops chaos or the<br />console API.</div>")]
        style 171 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 176 ["CloudFront + S3"]
        style 176 fill:#ffffff,stroke:#444444,color:#444444

        177["<div style='font-weight: bold'>incident console</div><div style='font-size: 70%; margin-top: 0px'>[Container: Static site on S3 + CloudFront at triage.serhiykucherenko.dev]</div><div style='font-size: 80%; margin-top:10px'>Live alert list, verdicts,<br />known-issues editor.</div>"]
        style 177 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 179 ["S3"]
        style 179 fill:#ffffff,stroke:#444444,color:#444444

        180[("<div style='font-weight: bold'>known-issues bucket</div><div style='font-size: 70%; margin-top: 0px'>[Container: S3]</div><div style='font-size: 80%; margin-top:10px'>Weekly JSON export of taught<br />known issues, so the memory<br />survives a table wipe;<br />expires after 30 days.</div>")]
        style 180 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 182 ["SSM"]
        style 182 fill:#ffffff,stroke:#444444,color:#444444

        183["<div style='font-weight: bold'>secrets</div><div style='font-size: 70%; margin-top: 0px'>[Container: SSM Parameter Store (SecureString)]</div><div style='font-size: 80%; margin-top:10px'>Anthropic key and webhook<br />HMAC secret.</div>"]
        style 183 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 185 ["CloudWatch"]
        style 185 fill:#ffffff,stroke:#444444,color:#444444

        186["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p95, DLQ depth, SLO<br />attainment; five ops alarms.</div>"]
        style 186 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 189 ["Route 53"]
        style 189 fill:#ffffff,stroke:#444444,color:#444444

        190["<div style='font-weight: bold'>dns</div><div style='font-size: 70%; margin-top: 0px'>[Container: Route 53 hosted zone]</div><div style='font-size: 80%; margin-top:10px'>DNSSEC-signed; query logs</div>"]
        style 190 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 191 ["ECR"]
        style 191 fill:#ffffff,stroke:#444444,color:#444444

        192["<div style='font-weight: bold'>triage-worker image</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>Immutable image tagged by git<br />SHA (also `:latest`); built<br />and pushed by deploy.yml's<br />`image` job, run by the<br />Lambda above.</div>"]
        style 192 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 193 ["AWS (us-east-1)"]
      style 193 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 194 ["KMS"]
        style 194 fill:#ffffff,stroke:#444444,color:#444444

        195["<div style='font-weight: bold'>DNSSEC signing key</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>ECC_NIST_P256 asymmetric key<br />(SIGN_VERIFY); Route 53<br />requires it in us-east-1<br />regardless of the stack's own<br />region.</div>"]
        style 195 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 196 ["Azure"]
      style 196 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 197 ["Function App (consumption)"]
        style 197 fill:#ffffff,stroke:#444444,color:#444444

        198["<div style='font-weight: bold'>customer-notifications</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>SMS / e-mail fan-out. Chaos:<br />provider-429, backlog.</div>"]
        style 198 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        200["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
        style 200 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 202 ["Application Insights + Log Analytics"]
        style 202 fill:#ffffff,stroke:#444444,color:#444444

        203["<div style='font-weight: bold'>Application Insights</div><div style='font-size: 70%; margin-top: 0px'>[Container: Application Insights + Log Analytics]</div><div style='font-size: 80%; margin-top:10px'>Custom metrics (provider_429,<br />notifications_backlog) and<br />exceptions from<br />customer-notifications; the<br />alert rules query it.</div>"]
        style 203 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 205 ["Azure Monitor"]
        style 205 fill:#ffffff,stroke:#444444,color:#444444

        206["<div style='font-weight: bold'>Azure Monitor</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Monitor]</div><div style='font-size: 80%; margin-top:10px'>Metric alert rules + action<br />group.</div>"]
        style 206 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 208 ["Anthropic"]
      style 208 fill:#ffffff,stroke:#444444,color:#444444

      209["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
      style 209 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    end

    subgraph 211 ["Cloudflare"]
      style 211 fill:#ffffff,stroke:#444444,color:#444444

      212["<div style='font-weight: bold'>NS delegation</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div>"]
      style 212 fill:#ffffff,stroke:#444444,color:#444444
    end

    138-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->148
    148-. "<div>triggers</div><div style='font-size: 70%'></div>" .->139
    140-. "<div>enqueue authorisation</div><div style='font-size: 70%'></div>" .->151
    151-. "<div>triggers</div><div style='font-size: 70%'></div>" .->141
    155-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->138
    140-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->155
    141-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->155
    142-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->155
    138-. "<div>alarm state change<br />(IngestErrorRatio)</div><div style='font-size: 70%'></div>" .->160
    139-. "<div>alarm state change<br />(WorkerErrors,<br />WorkerDurationP95,<br />CapReached)</div><div style='font-size: 70%'></div>" .->160
    148-. "<div>alarm state change<br />(AlertsDlqDepth)</div><div style='font-size: 70%'></div>" .->160
    138-. "<div>put alert</div><div style='font-size: 70%'></div>" .->165
    139-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->165
    143-. "<div>reads yesterday</div><div style='font-size: 70%'></div>" .->165
    144-. "<div>scans known issues</div><div style='font-size: 70%'></div>" .->165
    146-. "<div>query / put</div><div style='font-size: 70%'></div>" .->165
    140-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->171
    141-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->171
    142-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->171
    146-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->171
    177-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->146
    144-. "<div>put known-issues-<date>.json</div><div style='font-size: 70%'></div>" .->180
    139-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->183
    139-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->186
    143-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->186
    198-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->146
    200-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->138
    198-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->203
    206-. "<div>action group webhook (common<br />alert schema)</div><div style='font-size: 70%'>[HTTPS]</div>" .->200
    139-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->209

  end
```

## Deployment — where the Kubernetes estate runs (laptop, GitHub Actions)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: kind"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 213 ["Laptop"]
      style 213 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 214 ["kind cluster"]
        style 214 fill:#ffffff,stroke:#444444,color:#444444

        215["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 215 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        216["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 216 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        217["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 217 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        218["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
        style 218 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        222["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
        style 222 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        224["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
        style 224 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        226["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
        style 226 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        228["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
        style 228 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        236["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
        style 236 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 239 ["GitHub Actions runner"]
      style 239 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 240 ["kind cluster"]
        style 240 fill:#ffffff,stroke:#444444,color:#444444

        241["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 241 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        244["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 244 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        247["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 247 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        250["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
        style 250 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        261["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
        style 261 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        265["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
        style 265 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        270["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
        style 270 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        274["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
        style 274 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        290["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
        style 290 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    215-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->218
    216-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->218
    217-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->218
    222-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->218
    224-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->218
    226-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->215
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->216
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->217
    228-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->222
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->224
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->226
    236-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->224
    228-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->236
    241-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->241
    244-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->244
    247-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->247
    215-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->250
    216-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->250
    217-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->250
    222-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->250
    224-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->250
    226-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->250
    228-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->250
    241-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->250
    244-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->250
    247-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->250
    261-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->261
    261-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->250
    265-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->265
    236-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->265
    265-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->250
    270-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->218
    228-. "<div>scrape</div><div style='font-size: 70%'></div>" .->270
    270-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->250
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->215
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->216
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->217
    274-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->218
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->222
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->224
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->226
    274-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->236
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->241
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->244
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->247
    274-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->250
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->261
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->265
    274-. "<div>scrape</div><div style='font-size: 70%'></div>" .->270
    290-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->224
    228-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->290
    290-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->265
    274-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->290

  end
```
