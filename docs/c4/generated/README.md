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
    21["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 21 fill:#1c2530,stroke:#131921,color:#ffffff
    28["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 28 fill:#1c2530,stroke:#131921,color:#ffffff
    3["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
    style 3 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff

    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->21
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->28
    21-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->5
    5-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->21
    28-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    5-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3

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
    21["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 21 fill:#1c2530,stroke:#131921,color:#ffffff
    28["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 28 fill:#1c2530,stroke:#131921,color:#ffffff

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
      20["<div style='font-weight: bold'>dns</div><div style='font-size: 70%; margin-top: 0px'>[Container: Route 53 hosted zone]</div><div style='font-size: 80%; margin-top:10px'>DNSSEC-signed; query logs</div>"]
      style 20 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      7["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
      style 7 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      8["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
      style 8 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->17
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->21
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->28
    21-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->6
    16-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->21
    28-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    28-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    6-. "<div>put alert</div><div style='font-size: 70%'></div>" .->15
    6-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->7
    7-. "<div>triggers</div><div style='font-size: 70%'></div>" .->8
    8-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->15
    8-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->18
    8-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->19
    8-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->3
    17-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    16-. "<div>query / put</div><div style='font-size: 70%'></div>" .->15

  end
```

## Level 2 — the Kubernetes estate: services, Prometheus, Alertmanager route B

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Container View: Nordwind Kubernetes estate (kind)"]
    style diagram fill:#ffffff,stroke:#ffffff

    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    28["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 28 fill:#1c2530,stroke:#131921,color:#ffffff

    subgraph 33 ["Nordwind Kubernetes estate (kind)"]
      style 33 fill:#ffffff,stroke:#131921,color:#131921

      34["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
      style 34 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      35["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
      style 35 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      36["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
      style 36 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      37["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes the three services'<br />/metrics every 15s; evaluates<br />the six PrometheusRules.</div>"]
      style 37 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      38["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-b-forwarder (webhook).</div>"]
      style 38 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->28
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->34
    28-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    37-. "<div>scrape</div><div style='font-size: 70%'></div>" .->34
    37-. "<div>scrape</div><div style='font-size: 70%'></div>" .->35
    37-. "<div>scrape</div><div style='font-size: 70%'></div>" .->36
    37-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->38
    38-. "<div>route B webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->28

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

    9-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14
    10-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14
    11-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14
    14-. "<div>HTTPS</div><div style='font-size: 70%'></div>" .->3
    9-. "<div>get_alert, get_recent_alerts,<br />check_known, remember_issue</div><div style='font-size: 70%'></div>" .->12
    9-. "<div>transfer: new error</div><div style='font-size: 70%'></div>" .->10
    9-. "<div>transfer: known or<br />characterised error</div><div style='font-size: 70%'></div>" .->11
    10-. "<div>characterisation, via the<br />root agent</div><div style='font-size: 70%'></div>" .->11
    12-. "<div>find_known / add_known</div><div style='font-size: 70%'></div>" .->13
    13-. "<div>DynamoStore reads/writes</div><div style='font-size: 70%'></div>" .->15
    12-. "<div>get_alert / get_recent_alerts</div><div style='font-size: 70%'></div>" .->15

  end
```

## Deployment — where every container runs in `demo` (AWS, Azure)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: demo"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 104 ["AWS"]
      style 104 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 105 ["Lambda"]
        style 105 fill:#ffffff,stroke:#444444,color:#444444

        106["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
        style 106 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        107["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
        style 107 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        108["<div style='font-weight: bold'>payments</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Card payment authorisation<br />API. Chaos: errors, latency,<br />pool.</div>"]
        style 108 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        109["<div style='font-weight: bold'>ledger</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Double-entry posting worker<br />fed by SQS. Chaos:<br />reconciliation-mismatch, lag.</div>"]
        style 109 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        110["<div style='font-weight: bold'>auth</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Token issuance / JWKS. Chaos:<br />jwks-rotation, lockouts.</div>"]
        style 110 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 111 ["API Gateway"]
        style 111 fill:#ffffff,stroke:#444444,color:#444444

        112["<div style='font-weight: bold'>console API</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda + API Gateway HTTP API]</div><div style='font-size: 80%; margin-top:10px'>Reads alerts and verdicts;<br />accepts taught known issues.<br />Bearer-token protected (v1).</div>"]
        style 112 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 113 ["SQS"]
        style 113 fill:#ffffff,stroke:#444444,color:#444444

        114["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
        style 114 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        117["<div style='font-weight: bold'>ledger queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples payments from<br />ledger posting; DLQ after 5<br />failed attempts.</div>"]
        style 117 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 120 ["SNS"]
        style 120 fill:#ffffff,stroke:#444444,color:#444444

        121["<div style='font-weight: bold'>alarm topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>CloudWatch alarm state<br />changes fan out here.</div>"]
        style 121 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 126 ["DynamoDB"]
        style 126 fill:#ffffff,stroke:#444444,color:#444444

        127[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
        style 127 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        131[("<div style='font-weight: bold'>faults</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB]</div><div style='font-size: 80%; margin-top:10px'>One fault flag per service,<br />set by bankops chaos or the<br />console API.</div>")]
        style 131 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 136 ["CloudFront + S3"]
        style 136 fill:#ffffff,stroke:#444444,color:#444444

        137["<div style='font-weight: bold'>incident console</div><div style='font-size: 70%; margin-top: 0px'>[Container: Static site on S3 + CloudFront at triage.serhiykucherenko.dev]</div><div style='font-size: 80%; margin-top:10px'>Live alert list, verdicts,<br />known-issues editor.</div>"]
        style 137 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 139 ["SSM"]
        style 139 fill:#ffffff,stroke:#444444,color:#444444

        140["<div style='font-weight: bold'>secrets</div><div style='font-size: 70%; margin-top: 0px'>[Container: SSM Parameter Store (SecureString)]</div><div style='font-size: 80%; margin-top:10px'>Anthropic key and webhook<br />HMAC secret.</div>"]
        style 140 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 142 ["CloudWatch"]
        style 142 fill:#ffffff,stroke:#444444,color:#444444

        143["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard + alarms]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p50/p95, tokens per day, DLQ<br />depth; SLO 95% of verdicts<br />within 90 s.</div>"]
        style 143 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 145 ["Route 53"]
        style 145 fill:#ffffff,stroke:#444444,color:#444444

        146["<div style='font-weight: bold'>dns</div><div style='font-size: 70%; margin-top: 0px'>[Container: Route 53 hosted zone]</div><div style='font-size: 80%; margin-top:10px'>DNSSEC-signed; query logs</div>"]
        style 146 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 147 ["ECR"]
        style 147 fill:#ffffff,stroke:#444444,color:#444444

        148["<div style='font-weight: bold'>triage-worker image</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>Immutable image tagged by git<br />SHA (also `:latest`); built<br />and pushed by deploy.yml's<br />`image` job, run by the<br />Lambda above.</div>"]
        style 148 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 149 ["AWS (us-east-1)"]
      style 149 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 150 ["KMS"]
        style 150 fill:#ffffff,stroke:#444444,color:#444444

        151["<div style='font-weight: bold'>DNSSEC signing key</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>ECC_NIST_P256 asymmetric key<br />(SIGN_VERIFY); Route 53<br />requires it in us-east-1<br />regardless of the stack's own<br />region.</div>"]
        style 151 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 152 ["Azure"]
      style 152 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 153 ["Function App (consumption)"]
        style 153 fill:#ffffff,stroke:#444444,color:#444444

        154["<div style='font-weight: bold'>customer-notifications</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>SMS / e-mail fan-out. Chaos:<br />provider-429, backlog.</div>"]
        style 154 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        156["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
        style 156 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 158 ["Application Insights + Log Analytics"]
        style 158 fill:#ffffff,stroke:#444444,color:#444444

        159["<div style='font-weight: bold'>Application Insights</div><div style='font-size: 70%; margin-top: 0px'>[Container: Application Insights + Log Analytics]</div><div style='font-size: 80%; margin-top:10px'>Custom metrics (provider_429,<br />notifications_backlog) and<br />exceptions from<br />customer-notifications; the<br />alert rules query it.</div>"]
        style 159 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 161 ["Azure Monitor"]
        style 161 fill:#ffffff,stroke:#444444,color:#444444

        162["<div style='font-weight: bold'>Azure Monitor</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Monitor]</div><div style='font-size: 80%; margin-top:10px'>Metric alert rules + action<br />group.</div>"]
        style 162 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 164 ["Anthropic"]
      style 164 fill:#ffffff,stroke:#444444,color:#444444

      165["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
      style 165 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    end

    subgraph 167 ["Cloudflare"]
      style 167 fill:#ffffff,stroke:#444444,color:#444444

      168["<div style='font-weight: bold'>NS delegation</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div>"]
      style 168 fill:#ffffff,stroke:#444444,color:#444444
    end

    106-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->114
    114-. "<div>triggers</div><div style='font-size: 70%'></div>" .->107
    108-. "<div>enqueue authorisation</div><div style='font-size: 70%'></div>" .->117
    117-. "<div>triggers</div><div style='font-size: 70%'></div>" .->109
    121-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->106
    108-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->121
    109-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->121
    110-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->121
    106-. "<div>put alert</div><div style='font-size: 70%'></div>" .->127
    107-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->127
    112-. "<div>query / put</div><div style='font-size: 70%'></div>" .->127
    108-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->131
    109-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->131
    110-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->131
    112-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->131
    137-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->112
    107-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->140
    107-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->143
    154-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->112
    156-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->106
    154-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->159
    162-. "<div>action group webhook (common<br />alert schema)</div><div style='font-size: 70%'>[HTTPS]</div>" .->156
    107-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->165

  end
```

## Deployment — where the Kubernetes estate runs (laptop, GitHub Actions)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: kind"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 169 ["Laptop"]
      style 169 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 170 ["kind cluster"]
        style 170 fill:#ffffff,stroke:#444444,color:#444444

        171["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 171 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        172["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 172 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        173["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 173 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        174["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes the three services'<br />/metrics every 15s; evaluates<br />the six PrometheusRules.</div>"]
        style 174 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        178["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-b-forwarder (webhook).</div>"]
        style 178 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 180 ["GitHub Actions runner"]
      style 180 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 181 ["kind cluster"]
        style 181 fill:#ffffff,stroke:#444444,color:#444444

        182["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 182 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        184["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 184 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        186["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 186 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        188["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes the three services'<br />/metrics every 15s; evaluates<br />the six PrometheusRules.</div>"]
        style 188 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        196["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-b-forwarder (webhook).</div>"]
        style 196 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    174-. "<div>scrape</div><div style='font-size: 70%'></div>" .->171
    174-. "<div>scrape</div><div style='font-size: 70%'></div>" .->172
    174-. "<div>scrape</div><div style='font-size: 70%'></div>" .->173
    174-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->178
    174-. "<div>scrape</div><div style='font-size: 70%'></div>" .->182
    174-. "<div>scrape</div><div style='font-size: 70%'></div>" .->184
    174-. "<div>scrape</div><div style='font-size: 70%'></div>" .->186
    188-. "<div>scrape</div><div style='font-size: 70%'></div>" .->171
    188-. "<div>scrape</div><div style='font-size: 70%'></div>" .->172
    188-. "<div>scrape</div><div style='font-size: 70%'></div>" .->173
    188-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->178
    188-. "<div>scrape</div><div style='font-size: 70%'></div>" .->182
    188-. "<div>scrape</div><div style='font-size: 70%'></div>" .->184
    188-. "<div>scrape</div><div style='font-size: 70%'></div>" .->186
    174-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->196
    188-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->196

  end
```
