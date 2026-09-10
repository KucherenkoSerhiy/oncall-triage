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
    20["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 20 fill:#1c2530,stroke:#131921,color:#ffffff
    27["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 27 fill:#1c2530,stroke:#131921,color:#ffffff
    3["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
    style 3 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    32["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 32 fill:#1c2530,stroke:#131921,color:#ffffff
    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff

    32-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    5-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3
    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->20
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->32
    20-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->5
    5-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->20
    27-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    32-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5

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
    20["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 20 fill:#1c2530,stroke:#131921,color:#ffffff
    27["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 27 fill:#1c2530,stroke:#131921,color:#ffffff
    32["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 32 fill:#1c2530,stroke:#131921,color:#ffffff

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
      19["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard + alarms]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p50/p95, tokens per day, DLQ<br />depth; SLO 95% of verdicts<br />within 90 s.</div>"]
      style 19 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      7["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
      style 7 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      8["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
      style 8 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    32-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    6-. "<div>put alert</div><div style='font-size: 70%'></div>" .->15
    6-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->7
    7-. "<div>triggers</div><div style='font-size: 70%'></div>" .->8
    8-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->15
    8-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->18
    8-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->19
    8-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3
    17-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    16-. "<div>query / put</div><div style='font-size: 70%'></div>" .->15
    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->17
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->20
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->32
    20-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->6
    16-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->20
    27-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    27-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    32-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->6

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
    27["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 27 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 32 ["Nordwind Kubernetes estate (kind)"]
      style 32 fill:#ffffff,stroke:#131921,color:#131921

      33["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
      style 33 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      34["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
      style 34 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      35["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
      style 35 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      36["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
      style 36 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      37["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
      style 37 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      38["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
      style 38 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      39["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
      style 39 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      40["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 40 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      41["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->33
    27-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    40-. "<div>scrape</div><div style='font-size: 70%'></div>" .->33
    40-. "<div>scrape</div><div style='font-size: 70%'></div>" .->34
    40-. "<div>scrape</div><div style='font-size: 70%'></div>" .->35
    40-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->36
    40-. "<div>scrape</div><div style='font-size: 70%'></div>" .->37
    40-. "<div>scrape</div><div style='font-size: 70%'></div>" .->38
    40-. "<div>scrape</div><div style='font-size: 70%'></div>" .->39
    40-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->41
    33-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->36
    34-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->36
    35-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->36
    37-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->36
    41-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->38
    38-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->36
    39-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->36
    39-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5
    41-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->27

  end
```

## Dynamic — an alert travels over Kafka (route A)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Dynamic View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 32 ["Nordwind Kubernetes estate (kind)"]
      style 32 fill:#ffffff,stroke:#131921,color:#131921

      36["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
      style 36 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      38["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
      style 38 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      39["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
      style 39 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      40["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 40 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      41["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    40-. "<div>1. rule fires</div><div style='font-size: 70%'></div>" .->41
    41-. "<div>2. route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->38
    38-. "<div>3. produce alerts.raw</div><div style='font-size: 70%'></div>" .->36
    39-. "<div>4. consume alerts.raw</div><div style='font-size: 70%'></div>" .->36
    39-. "<div>5. HTTPS + HMAC</div><div style='font-size: 70%'></div>" .->6

  end
```

## Dynamic — the alert about Kafka takes route B

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Dynamic View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 27 ["Nordwind serverless estate (Azure)"]
      style 27 fill:#ffffff,stroke:#131921,color:#131921

      31["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
      style 31 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 32 ["Nordwind Kubernetes estate (kind)"]
      style 32 fill:#ffffff,stroke:#131921,color:#131921

      40["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 40 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      41["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    40-. "<div>1. KafkaBrokerDown fires</div><div style='font-size: 70%'></div>" .->41
    41-. "<div>2. route B webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->31
    31-. "<div>3. HTTPS + HMAC</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6

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

    subgraph 122 ["AWS"]
      style 122 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 123 ["Lambda"]
        style 123 fill:#ffffff,stroke:#444444,color:#444444

        124["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
        style 124 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        125["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
        style 125 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        126["<div style='font-weight: bold'>payments</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Card payment authorisation<br />API. Chaos: errors, latency,<br />pool.</div>"]
        style 126 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        127["<div style='font-weight: bold'>ledger</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Double-entry posting worker<br />fed by SQS. Chaos:<br />reconciliation-mismatch, lag.</div>"]
        style 127 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        128["<div style='font-weight: bold'>auth</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Token issuance / JWKS. Chaos:<br />jwks-rotation, lockouts.</div>"]
        style 128 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 129 ["API Gateway"]
        style 129 fill:#ffffff,stroke:#444444,color:#444444

        130["<div style='font-weight: bold'>console API</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda + API Gateway HTTP API]</div><div style='font-size: 80%; margin-top:10px'>Reads alerts and verdicts;<br />accepts taught known issues.<br />Bearer-token protected (v1).</div>"]
        style 130 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 131 ["SQS"]
        style 131 fill:#ffffff,stroke:#444444,color:#444444

        132["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
        style 132 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        135["<div style='font-weight: bold'>ledger queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples payments from<br />ledger posting; DLQ after 5<br />failed attempts.</div>"]
        style 135 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 138 ["SNS"]
        style 138 fill:#ffffff,stroke:#444444,color:#444444

        139["<div style='font-weight: bold'>alarm topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>CloudWatch alarm state<br />changes fan out here.</div>"]
        style 139 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 144 ["DynamoDB"]
        style 144 fill:#ffffff,stroke:#444444,color:#444444

        145[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
        style 145 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        149[("<div style='font-weight: bold'>faults</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB]</div><div style='font-size: 80%; margin-top:10px'>One fault flag per service,<br />set by bankops chaos or the<br />console API.</div>")]
        style 149 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 154 ["CloudFront + S3"]
        style 154 fill:#ffffff,stroke:#444444,color:#444444

        155["<div style='font-weight: bold'>incident console</div><div style='font-size: 70%; margin-top: 0px'>[Container: Static site on S3 + CloudFront at triage.serhiykucherenko.dev]</div><div style='font-size: 80%; margin-top:10px'>Live alert list, verdicts,<br />known-issues editor.</div>"]
        style 155 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 157 ["SSM"]
        style 157 fill:#ffffff,stroke:#444444,color:#444444

        158["<div style='font-weight: bold'>secrets</div><div style='font-size: 70%; margin-top: 0px'>[Container: SSM Parameter Store (SecureString)]</div><div style='font-size: 80%; margin-top:10px'>Anthropic key and webhook<br />HMAC secret.</div>"]
        style 158 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 160 ["CloudWatch"]
        style 160 fill:#ffffff,stroke:#444444,color:#444444

        161["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard + alarms]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p50/p95, tokens per day, DLQ<br />depth; SLO 95% of verdicts<br />within 90 s.</div>"]
        style 161 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 163 ["ECR"]
        style 163 fill:#ffffff,stroke:#444444,color:#444444

        164["<div style='font-weight: bold'>triage-worker image</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>Immutable image tagged by git<br />SHA (also `:latest`); built<br />and pushed by deploy.yml's<br />`image` job, run by the<br />Lambda above.</div>"]
        style 164 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 165 ["Azure"]
      style 165 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 166 ["Function App (consumption)"]
        style 166 fill:#ffffff,stroke:#444444,color:#444444

        167["<div style='font-weight: bold'>customer-notifications</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>SMS / e-mail fan-out. Chaos:<br />provider-429, backlog.</div>"]
        style 167 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        169["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
        style 169 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 171 ["Application Insights + Log Analytics"]
        style 171 fill:#ffffff,stroke:#444444,color:#444444

        172["<div style='font-weight: bold'>Application Insights</div><div style='font-size: 70%; margin-top: 0px'>[Container: Application Insights + Log Analytics]</div><div style='font-size: 80%; margin-top:10px'>Custom metrics (provider_429,<br />notifications_backlog) and<br />exceptions from<br />customer-notifications; the<br />alert rules query it.</div>"]
        style 172 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 174 ["Azure Monitor"]
        style 174 fill:#ffffff,stroke:#444444,color:#444444

        175["<div style='font-weight: bold'>Azure Monitor</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Monitor]</div><div style='font-size: 80%; margin-top:10px'>Metric alert rules + action<br />group.</div>"]
        style 175 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 177 ["Anthropic"]
      style 177 fill:#ffffff,stroke:#444444,color:#444444

      178["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
      style 178 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    end

    subgraph 180 ["Cloudflare"]
      style 180 fill:#ffffff,stroke:#444444,color:#444444

      181["<div style='font-weight: bold'>NS delegation</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div>"]
      style 181 fill:#ffffff,stroke:#444444,color:#444444
    end

    124-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->132
    132-. "<div>triggers</div><div style='font-size: 70%'></div>" .->125
    126-. "<div>enqueue authorisation</div><div style='font-size: 70%'></div>" .->135
    135-. "<div>triggers</div><div style='font-size: 70%'></div>" .->127
    139-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->124
    126-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->139
    127-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->139
    128-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->139
    124-. "<div>put alert</div><div style='font-size: 70%'></div>" .->145
    125-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->145
    130-. "<div>query / put</div><div style='font-size: 70%'></div>" .->145
    126-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->149
    127-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->149
    128-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->149
    130-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->149
    155-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->130
    125-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->158
    125-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->161
    167-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->130
    169-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->124
    167-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->172
    175-. "<div>action group webhook (common<br />alert schema)</div><div style='font-size: 70%'>[HTTPS]</div>" .->169
    125-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->178

  end
```

## Deployment — where the Kubernetes estate runs (laptop, GitHub Actions)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: kind"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 182 ["Laptop"]
      style 182 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 183 ["kind cluster"]
        style 183 fill:#ffffff,stroke:#444444,color:#444444

        184["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 184 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        185["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 185 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        186["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 186 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        187["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
        style 187 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        191["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
        style 191 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        193["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
        style 193 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        195["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
        style 195 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        197["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
        style 197 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        205["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
        style 205 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 208 ["GitHub Actions runner"]
      style 208 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 209 ["kind cluster"]
        style 209 fill:#ffffff,stroke:#444444,color:#444444

        210["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 210 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        213["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 213 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        216["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 216 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        219["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
        style 219 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        230["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
        style 230 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        234["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
        style 234 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        239["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
        style 239 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        243["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
        style 243 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        259["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
        style 259 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    184-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->187
    185-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->187
    186-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->187
    191-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->187
    193-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->187
    195-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->184
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->185
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->186
    197-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->191
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->193
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->195
    205-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->193
    197-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->205
    210-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->210
    213-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->213
    216-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->216
    184-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->219
    185-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->219
    186-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->219
    191-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->219
    193-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->219
    195-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->219
    197-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->219
    210-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->219
    213-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->219
    216-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->219
    230-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->230
    230-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->219
    234-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->234
    205-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->234
    234-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->219
    239-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->187
    197-. "<div>scrape</div><div style='font-size: 70%'></div>" .->239
    239-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->219
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->184
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->185
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->186
    243-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->187
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->191
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->193
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->195
    243-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->205
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->210
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->213
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->216
    243-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->219
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->230
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->234
    243-. "<div>scrape</div><div style='font-size: 70%'></div>" .->239
    259-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->193
    197-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->259
    259-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->234
    243-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->259

  end
```
