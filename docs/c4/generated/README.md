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
    22["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 22 fill:#1c2530,stroke:#131921,color:#ffffff
    29["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 29 fill:#1c2530,stroke:#131921,color:#ffffff
    3["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
    style 3 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    34["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 34 fill:#1c2530,stroke:#131921,color:#ffffff
    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff

    34-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->29
    5-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3
    5-. "<div>e-mail notification</div><div style='font-size: 70%'></div>" .->1
    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->22
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->29
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->34
    22-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->5
    5-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->22
    29-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    34-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5

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
    22["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 22 fill:#1c2530,stroke:#131921,color:#ffffff
    29["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 29 fill:#1c2530,stroke:#131921,color:#ffffff
    34["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 34 fill:#1c2530,stroke:#131921,color:#ffffff

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
      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      7["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
      style 7 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      8["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
      style 8 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    34-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->29
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
    6-. "<div>alarm state change<br />(IngestErrorRatio)</div><div style='font-size: 70%'></div>" .->20
    8-. "<div>alarm state change<br />(WorkerErrors,<br />WorkerDurationP95,<br />CapReached)</div><div style='font-size: 70%'></div>" .->20
    7-. "<div>alarm state change<br />(AlertsDlqDepth)</div><div style='font-size: 70%'></div>" .->20
    20-. "<div>e-mail notification</div><div style='font-size: 70%'></div>" .->1
    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->17
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->22
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->29
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->34
    22-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->6
    16-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->22
    29-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    29-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    34-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->6

  end
```

## Level 2 — the AWS estate: payments, ledger, auth, CloudWatch alarms

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Container View: Nordwind serverless estate (AWS)"]
    style diagram fill:#ffffff,stroke:#ffffff

    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 22 ["Nordwind serverless estate (AWS)"]
      style 22 fill:#ffffff,stroke:#131921,color:#131921

      23["<div style='font-weight: bold'>payments</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Card payment authorisation<br />API. Chaos: errors, latency,<br />pool.</div>"]
      style 23 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      24["<div style='font-weight: bold'>ledger queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples payments from<br />ledger posting; DLQ after 5<br />failed attempts.</div>"]
      style 24 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      25["<div style='font-weight: bold'>ledger</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Double-entry posting worker<br />fed by SQS. Chaos:<br />reconciliation-mismatch, lag.</div>"]
      style 25 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      26["<div style='font-weight: bold'>auth</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Token issuance / JWKS. Chaos:<br />jwks-rotation, lockouts.</div>"]
      style 26 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      27["<div style='font-weight: bold'>alarm topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>CloudWatch alarm state<br />changes fan out here.</div>"]
      style 27 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      28[("<div style='font-weight: bold'>faults</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB]</div><div style='font-size: 80%; margin-top:10px'>One fault flag per service,<br />set by bankops chaos or the<br />console API.</div>")]
      style 28 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->23
    23-. "<div>enqueue authorisation</div><div style='font-size: 70%'></div>" .->24
    24-. "<div>triggers</div><div style='font-size: 70%'></div>" .->25
    23-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->27
    25-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->27
    26-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->27
    27-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->5
    23-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->28
    25-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->28
    26-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->28
    5-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->28

  end
```

## Level 2 — the Azure estate: customer-notifications, Azure Monitor, forwarder

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Container View: Nordwind serverless estate (Azure)"]
    style diagram fill:#ffffff,stroke:#ffffff

    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff
    34["<div style='font-weight: bold'>Nordwind Kubernetes estate (kind)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services plus a<br />Kafka backbone on Kubernetes,<br />with Prometheus and<br />Alertmanager routing alerts<br />over Kafka (route A) or<br />straight to the forwarder<br />(route B, Kafka's own<br />alerts). Runs in kind on a<br />laptop or a GitHub Actions<br />runner.</div>"]
    style 34 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 29 ["Nordwind serverless estate (Azure)"]
      style 29 fill:#ffffff,stroke:#131921,color:#131921

      30["<div style='font-weight: bold'>customer-notifications</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>SMS / e-mail fan-out. Chaos:<br />provider-429, backlog.</div>"]
      style 30 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      31["<div style='font-weight: bold'>Application Insights</div><div style='font-size: 70%; margin-top: 0px'>[Container: Application Insights + Log Analytics]</div><div style='font-size: 80%; margin-top:10px'>Custom metrics (provider_429,<br />notifications_backlog) and<br />exceptions from<br />customer-notifications; the<br />alert rules query it.</div>"]
      style 31 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      32["<div style='font-weight: bold'>Azure Monitor</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Monitor]</div><div style='font-size: 80%; margin-top:10px'>Metric alert rules + action<br />group.</div>"]
      style 32 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      33["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
      style 33 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    34-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->33
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->30
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->34
    30-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    30-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->31
    32-. "<div>action group webhook (common<br />alert schema)</div><div style='font-size: 70%'>[HTTPS]</div>" .->33
    33-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    34-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5

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
    29["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 29 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 34 ["Nordwind Kubernetes estate (kind)"]
      style 34 fill:#ffffff,stroke:#131921,color:#131921

      35["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
      style 35 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      36["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
      style 36 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      37["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
      style 37 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      38["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
      style 38 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      39["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
      style 39 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      40["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
      style 40 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      41["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      42["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 42 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      43["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 43 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    43-. "<div>route B (Kafka's own alerts)</div><div style='font-size: 70%'>[HTTPS]</div>" .->29
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->29
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->35
    29-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    42-. "<div>scrape</div><div style='font-size: 70%'></div>" .->35
    42-. "<div>scrape</div><div style='font-size: 70%'></div>" .->36
    42-. "<div>scrape</div><div style='font-size: 70%'></div>" .->37
    42-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->38
    42-. "<div>scrape</div><div style='font-size: 70%'></div>" .->39
    42-. "<div>scrape</div><div style='font-size: 70%'></div>" .->40
    42-. "<div>scrape</div><div style='font-size: 70%'></div>" .->41
    42-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->43
    35-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->38
    36-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->38
    37-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->38
    39-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->38
    43-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->40
    40-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->38
    41-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->38
    41-. "<div>HTTPS + HMAC (route A)</div><div style='font-size: 70%'></div>" .->5

  end
```

## Dynamic — an alert travels over Kafka (route A)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Dynamic View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 34 ["Nordwind Kubernetes estate (kind)"]
      style 34 fill:#ffffff,stroke:#131921,color:#131921

      38["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
      style 38 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      40["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
      style 40 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      41["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
      style 41 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      42["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 42 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      43["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 43 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    42-. "<div>1. rule fires</div><div style='font-size: 70%'></div>" .->43
    43-. "<div>2. route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->40
    40-. "<div>3. produce alerts.raw</div><div style='font-size: 70%'></div>" .->38
    41-. "<div>4. consume alerts.raw</div><div style='font-size: 70%'></div>" .->38
    41-. "<div>5. HTTPS + HMAC</div><div style='font-size: 70%'></div>" .->6

  end
```

## Dynamic — the alert about Kafka takes route B

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Dynamic View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 29 ["Nordwind serverless estate (Azure)"]
      style 29 fill:#ffffff,stroke:#131921,color:#131921

      33["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
      style 33 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 34 ["Nordwind Kubernetes estate (kind)"]
      style 34 fill:#ffffff,stroke:#131921,color:#131921

      42["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
      style 42 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      43["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
      style 43 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    42-. "<div>1. KafkaBrokerDown fires</div><div style='font-size: 70%'></div>" .->43
    43-. "<div>2. route B webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->33
    33-. "<div>3. HTTPS + HMAC</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6

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

    subgraph 131 ["AWS"]
      style 131 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 132 ["Lambda"]
        style 132 fill:#ffffff,stroke:#444444,color:#444444

        133["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
        style 133 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        134["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
        style 134 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        135["<div style='font-weight: bold'>payments</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Card payment authorisation<br />API. Chaos: errors, latency,<br />pool.</div>"]
        style 135 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        136["<div style='font-weight: bold'>ledger</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Double-entry posting worker<br />fed by SQS. Chaos:<br />reconciliation-mismatch, lag.</div>"]
        style 136 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        137["<div style='font-weight: bold'>auth</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Token issuance / JWKS. Chaos:<br />jwks-rotation, lockouts.</div>"]
        style 137 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        138["<div style='font-weight: bold'>slo-reporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Daily (00:15 UTC): reads<br />yesterday's triaged alerts<br />and verdicts, computes<br />latency p95 and SLO<br />attainment.</div>"]
        style 138 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 139 ["API Gateway"]
        style 139 fill:#ffffff,stroke:#444444,color:#444444

        140["<div style='font-weight: bold'>console API</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda + API Gateway HTTP API]</div><div style='font-size: 80%; margin-top:10px'>Reads alerts and verdicts;<br />accepts taught known issues.<br />Bearer-token protected (v1).</div>"]
        style 140 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 141 ["SQS"]
        style 141 fill:#ffffff,stroke:#444444,color:#444444

        142["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
        style 142 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        145["<div style='font-weight: bold'>ledger queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples payments from<br />ledger posting; DLQ after 5<br />failed attempts.</div>"]
        style 145 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 148 ["SNS"]
        style 148 fill:#ffffff,stroke:#444444,color:#444444

        149["<div style='font-weight: bold'>alarm topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>CloudWatch alarm state<br />changes fan out here.</div>"]
        style 149 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        154["<div style='font-weight: bold'>ops topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>Human-only: CloudWatch alarm<br />state changes for the triage<br />brain itself, never fed back<br />into ingest.</div>"]
        style 154 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 158 ["DynamoDB"]
        style 158 fill:#ffffff,stroke:#444444,color:#444444

        159[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
        style 159 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        164[("<div style='font-weight: bold'>faults</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB]</div><div style='font-size: 80%; margin-top:10px'>One fault flag per service,<br />set by bankops chaos or the<br />console API.</div>")]
        style 164 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 169 ["CloudFront + S3"]
        style 169 fill:#ffffff,stroke:#444444,color:#444444

        170["<div style='font-weight: bold'>incident console</div><div style='font-size: 70%; margin-top: 0px'>[Container: Static site on S3 + CloudFront at triage.serhiykucherenko.dev]</div><div style='font-size: 80%; margin-top:10px'>Live alert list, verdicts,<br />known-issues editor.</div>"]
        style 170 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 172 ["SSM"]
        style 172 fill:#ffffff,stroke:#444444,color:#444444

        173["<div style='font-weight: bold'>secrets</div><div style='font-size: 70%; margin-top: 0px'>[Container: SSM Parameter Store (SecureString)]</div><div style='font-size: 80%; margin-top:10px'>Anthropic key and webhook<br />HMAC secret.</div>"]
        style 173 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 175 ["CloudWatch"]
        style 175 fill:#ffffff,stroke:#444444,color:#444444

        176["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p95, DLQ depth, SLO<br />attainment; five ops alarms.</div>"]
        style 176 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 179 ["ECR"]
        style 179 fill:#ffffff,stroke:#444444,color:#444444

        180["<div style='font-weight: bold'>triage-worker image</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>Immutable image tagged by git<br />SHA (also `:latest`); built<br />and pushed by deploy.yml's<br />`image` job, run by the<br />Lambda above.</div>"]
        style 180 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 181 ["Azure"]
      style 181 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 182 ["Function App (consumption)"]
        style 182 fill:#ffffff,stroke:#444444,color:#444444

        183["<div style='font-weight: bold'>customer-notifications</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>SMS / e-mail fan-out. Chaos:<br />provider-429, backlog.</div>"]
        style 183 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        185["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
        style 185 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 187 ["Application Insights + Log Analytics"]
        style 187 fill:#ffffff,stroke:#444444,color:#444444

        188["<div style='font-weight: bold'>Application Insights</div><div style='font-size: 70%; margin-top: 0px'>[Container: Application Insights + Log Analytics]</div><div style='font-size: 80%; margin-top:10px'>Custom metrics (provider_429,<br />notifications_backlog) and<br />exceptions from<br />customer-notifications; the<br />alert rules query it.</div>"]
        style 188 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 190 ["Azure Monitor"]
        style 190 fill:#ffffff,stroke:#444444,color:#444444

        191["<div style='font-weight: bold'>Azure Monitor</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Monitor]</div><div style='font-size: 80%; margin-top:10px'>Metric alert rules + action<br />group.</div>"]
        style 191 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 193 ["Anthropic"]
      style 193 fill:#ffffff,stroke:#444444,color:#444444

      194["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
      style 194 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    end

    subgraph 196 ["Cloudflare"]
      style 196 fill:#ffffff,stroke:#444444,color:#444444

      197["<div style='font-weight: bold'>NS delegation</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div>"]
      style 197 fill:#ffffff,stroke:#444444,color:#444444
    end

    133-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->142
    142-. "<div>triggers</div><div style='font-size: 70%'></div>" .->134
    135-. "<div>enqueue authorisation</div><div style='font-size: 70%'></div>" .->145
    145-. "<div>triggers</div><div style='font-size: 70%'></div>" .->136
    149-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->133
    135-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->149
    136-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->149
    137-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->149
    133-. "<div>alarm state change<br />(IngestErrorRatio)</div><div style='font-size: 70%'></div>" .->154
    134-. "<div>alarm state change<br />(WorkerErrors,<br />WorkerDurationP95,<br />CapReached)</div><div style='font-size: 70%'></div>" .->154
    142-. "<div>alarm state change<br />(AlertsDlqDepth)</div><div style='font-size: 70%'></div>" .->154
    133-. "<div>put alert</div><div style='font-size: 70%'></div>" .->159
    134-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->159
    138-. "<div>reads yesterday</div><div style='font-size: 70%'></div>" .->159
    140-. "<div>query / put</div><div style='font-size: 70%'></div>" .->159
    135-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->164
    136-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->164
    137-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->164
    140-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->164
    170-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->140
    134-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->173
    134-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->176
    138-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->176
    183-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->140
    185-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->133
    183-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->188
    191-. "<div>action group webhook (common<br />alert schema)</div><div style='font-size: 70%'>[HTTPS]</div>" .->185
    134-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->194

  end
```

## Deployment — where the Kubernetes estate runs (laptop, GitHub Actions)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: kind"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 198 ["Laptop"]
      style 198 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 199 ["kind cluster"]
        style 199 fill:#ffffff,stroke:#444444,color:#444444

        200["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 200 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        201["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 201 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        202["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 202 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        203["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
        style 203 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        207["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
        style 207 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        209["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
        style 209 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        211["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
        style 211 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        213["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
        style 213 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        221["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
        style 221 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 224 ["GitHub Actions runner"]
      style 224 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 225 ["kind cluster"]
        style 225 fill:#ffffff,stroke:#444444,color:#444444

        226["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 226 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        229["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 229 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        232["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 232 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        235["<div style='font-weight: bold'>kafka</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi (KRaft)]</div><div style='font-size: 80%; margin-top:10px'>Business event backbone and<br />alert transport:<br />card.authorized,<br />fraud.scored, alerts.raw.</div>"]
        style 235 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        246["<div style='font-weight: bold'>kafka-exporter</div><div style='font-size: 70%; margin-top: 0px'>[Container: Strimzi kafka-exporter]</div><div style='font-size: 80%; margin-top:10px'>Exports per-consumer-group<br />lag<br />(kafka_consumergroup_lag).<br />Chaos: broker-down (scales<br />the broker KafkaNodePool to<br />0).</div>"]
        style 246 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        250["<div style='font-weight: bold'>alerts-bridge</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Alertmanager webhook<br />receiver; produces one Kafka<br />message per alert to<br />alerts.raw (route A's first<br />hop).</div>"]
        style 250 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        255["<div style='font-weight: bold'>kafka-relay</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>Consumes alerts.raw,<br />HMAC-signs, and POSTs to<br />ingest (route A's second<br />hop).</div>"]
        style 255 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        259["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes services, Kafka, and<br />kafka-exporter; evaluates the<br />eleven PrometheusRules.</div>"]
        style 259 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        275["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-a-kafka by default;<br />Kafka's own alerts<br />(KafkaBrokerDown,<br />KafkaRelayLag,<br />AlertsBridgeDown,<br />KafkaRelayDown) take<br />route-b-forwarder instead.</div>"]
        style 275 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    200-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->203
    201-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->203
    202-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->203
    207-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->203
    209-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->203
    211-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->200
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->201
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->202
    213-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->207
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->209
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->211
    221-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->209
    213-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->221
    226-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->226
    229-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->229
    232-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->232
    200-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->235
    201-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->235
    202-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->235
    207-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->235
    209-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->235
    211-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->235
    213-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->235
    226-. "<div>produce card.authorized</div><div style='font-size: 70%'></div>" .->235
    229-. "<div>consume card.authorized,<br />produce fraud.scored</div><div style='font-size: 70%'></div>" .->235
    232-. "<div>consume fraud.scored</div><div style='font-size: 70%'></div>" .->235
    246-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->246
    246-. "<div>read consumer group offsets</div><div style='font-size: 70%'></div>" .->235
    250-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->250
    221-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->250
    250-. "<div>produce alerts.raw</div><div style='font-size: 70%'></div>" .->235
    255-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->203
    213-. "<div>scrape</div><div style='font-size: 70%'></div>" .->255
    255-. "<div>consume alerts.raw</div><div style='font-size: 70%'></div>" .->235
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->200
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->201
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->202
    259-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->203
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->207
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->209
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->211
    259-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->221
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->226
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->229
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->232
    259-. "<div>scrape broker JMX</div><div style='font-size: 70%'></div>" .->235
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->246
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->250
    259-. "<div>scrape</div><div style='font-size: 70%'></div>" .->255
    275-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->209
    213-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->275
    275-. "<div>route A webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->250
    259-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->275

  end
```
