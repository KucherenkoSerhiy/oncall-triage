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
    4["<div style='font-weight: bold'>bankops CLI</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>fire, chaos, teach, tail,<br />estate up|down</div>"]
    style 4 fill:#5b6b7a,stroke:#3f4a55,color:#ffffff
    5["<div style='font-weight: bold'>Alert Triage</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Ingests alerts from every<br />estate, triages them with<br />Claude, remembers known<br />issues, publishes verdicts.</div>"]
    style 5 fill:#1c2530,stroke:#131921,color:#ffffff

    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->5
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->20
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    20-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->5
    5-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->20
    27-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->5
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
    20["<div style='font-weight: bold'>Nordwind serverless estate (AWS)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Three bank services on Lambda<br />with CloudWatch alarms.</div>"]
    style 20 fill:#1c2530,stroke:#131921,color:#ffffff
    27["<div style='font-weight: bold'>Nordwind serverless estate (Azure)</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>One bank service on Azure<br />Functions, Azure Monitor<br />alerts, and the always-on<br />alert forwarder.</div>"]
    style 27 fill:#1c2530,stroke:#131921,color:#ffffff

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

    1-. "<div>reads verdicts, teaches known<br />issues</div><div style='font-size: 70%'>[HTTPS]</div>" .->17
    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[Lambda invoke]</div>" .->20
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    20-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->6
    16-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->20
    27-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->16
    27-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
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
      36["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes the three services'<br />/metrics every 15s; evaluates<br />the six PrometheusRules.</div>"]
      style 36 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      37["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-b-forwarder (webhook).</div>"]
      style 37 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    subgraph 5 ["Alert Triage"]
      style 5 fill:#ffffff,stroke:#131921,color:#131921

      6["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
      style 6 fill:#14b8a6,stroke:#0e8074,color:#0e1419
    end

    4-. "<div>fire: synthetic alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    4-. "<div>chaos: set fault flag</div><div style='font-size: 70%'>[HTTPS]</div>" .->27
    4-. "<div>chaos: patch ConfigMap</div><div style='font-size: 70%'>[kubectl]</div>" .->33
    27-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->6
    36-. "<div>scrape</div><div style='font-size: 70%'></div>" .->33
    36-. "<div>scrape</div><div style='font-size: 70%'></div>" .->34
    36-. "<div>scrape</div><div style='font-size: 70%'></div>" .->35
    36-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->37
    37-. "<div>route B webhook</div><div style='font-size: 70%'>[HTTPS]</div>" .->27

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
    9-. "<div>model turns</div><div style='font-size: 70%'></div>" .->14

  end
```

## Deployment — where every container runs in `demo` (AWS, Azure)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: demo"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 103 ["AWS"]
      style 103 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 104 ["Lambda"]
        style 104 fill:#ffffff,stroke:#444444,color:#444444

        105["<div style='font-weight: bold'>ingest</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>HMAC-verifies webhooks,<br />normalises to the canonical<br />alert, scrubs PII, dedups by<br />fingerprint, enqueues.</div>"]
        style 105 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        106["<div style='font-weight: bold'>triage worker</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda container image (Python, Google ADK)]</div><div style='font-size: 80%; margin-top:10px'>Runs the three-role ADK<br />workflow once per alert and<br />writes the verdict.</div>"]
        style 106 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        107["<div style='font-weight: bold'>payments</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Card payment authorisation<br />API. Chaos: errors, latency,<br />pool.</div>"]
        style 107 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        108["<div style='font-weight: bold'>ledger</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Double-entry posting worker<br />fed by SQS. Chaos:<br />reconciliation-mismatch, lag.</div>"]
        style 108 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        109["<div style='font-weight: bold'>auth</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda (Python)]</div><div style='font-size: 80%; margin-top:10px'>Token issuance / JWKS. Chaos:<br />jwks-rotation, lockouts.</div>"]
        style 109 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 110 ["API Gateway"]
        style 110 fill:#ffffff,stroke:#444444,color:#444444

        111["<div style='font-weight: bold'>console API</div><div style='font-size: 70%; margin-top: 0px'>[Container: AWS Lambda + API Gateway HTTP API]</div><div style='font-size: 80%; margin-top:10px'>Reads alerts and verdicts;<br />accepts taught known issues.<br />Bearer-token protected (v1).</div>"]
        style 111 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 112 ["SQS"]
        style 112 fill:#ffffff,stroke:#444444,color:#444444

        113["<div style='font-weight: bold'>alerts queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples ingestion from LLM<br />latency; dead-letter queue<br />for poison alerts.</div>"]
        style 113 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        116["<div style='font-weight: bold'>ledger queue</div><div style='font-size: 70%; margin-top: 0px'>[Container: SQS + DLQ]</div><div style='font-size: 80%; margin-top:10px'>Decouples payments from<br />ledger posting; DLQ after 5<br />failed attempts.</div>"]
        style 116 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 119 ["SNS"]
        style 119 fill:#ffffff,stroke:#444444,color:#444444

        120["<div style='font-weight: bold'>alarm topic</div><div style='font-size: 70%; margin-top: 0px'>[Container: SNS]</div><div style='font-size: 80%; margin-top:10px'>CloudWatch alarm state<br />changes fan out here.</div>"]
        style 120 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 125 ["DynamoDB"]
        style 125 fill:#ffffff,stroke:#444444,color:#444444

        126[("<div style='font-weight: bold'>alerts, verdicts, known-issues</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB (3 tables)]</div><div style='font-size: 80%; margin-top:10px'>Alert log, one verdict per<br />alert, taught known issues<br />per service.</div>")]
        style 126 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        130[("<div style='font-weight: bold'>faults</div><div style='font-size: 70%; margin-top: 0px'>[Container: DynamoDB]</div><div style='font-size: 80%; margin-top:10px'>One fault flag per service,<br />set by bankops chaos or the<br />console API.</div>")]
        style 130 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 135 ["CloudFront + S3"]
        style 135 fill:#ffffff,stroke:#444444,color:#444444

        136["<div style='font-weight: bold'>incident console</div><div style='font-size: 70%; margin-top: 0px'>[Container: Static site on S3 + CloudFront at triage.serhiykucherenko.dev]</div><div style='font-size: 80%; margin-top:10px'>Live alert list, verdicts,<br />known-issues editor.</div>"]
        style 136 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 138 ["SSM"]
        style 138 fill:#ffffff,stroke:#444444,color:#444444

        139["<div style='font-weight: bold'>secrets</div><div style='font-size: 70%; margin-top: 0px'>[Container: SSM Parameter Store (SecureString)]</div><div style='font-size: 80%; margin-top:10px'>Anthropic key and webhook<br />HMAC secret.</div>"]
        style 139 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 141 ["CloudWatch"]
        style 141 fill:#ffffff,stroke:#444444,color:#444444

        142["<div style='font-weight: bold'>self-observability</div><div style='font-size: 70%; margin-top: 0px'>[Container: CloudWatch dashboard + alarms]</div><div style='font-size: 80%; margin-top:10px'>Ingest rate, verdict latency<br />p50/p95, tokens per day, DLQ<br />depth; SLO 95% of verdicts<br />within 90 s.</div>"]
        style 142 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 144 ["ECR"]
        style 144 fill:#ffffff,stroke:#444444,color:#444444

        145["<div style='font-weight: bold'>triage-worker image</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div><div style='font-size: 80%; margin-top:10px'>Immutable image tagged by git<br />SHA (also `:latest`); built<br />and pushed by deploy.yml's<br />`image` job, run by the<br />Lambda above.</div>"]
        style 145 fill:#ffffff,stroke:#444444,color:#444444
      end

    end

    subgraph 146 ["Azure"]
      style 146 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 147 ["Function App (consumption)"]
        style 147 fill:#ffffff,stroke:#444444,color:#444444

        148["<div style='font-weight: bold'>customer-notifications</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>SMS / e-mail fan-out. Chaos:<br />provider-429, backlog.</div>"]
        style 148 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        150["<div style='font-weight: bold'>alert forwarder</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Function (Python)]</div><div style='font-size: 80%; margin-top:10px'>Receives Azure Monitor<br />action-group calls and<br />Alertmanager route-B<br />webhooks, signs with HMAC,<br />posts to ingest.</div>"]
        style 150 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 152 ["Application Insights + Log Analytics"]
        style 152 fill:#ffffff,stroke:#444444,color:#444444

        153["<div style='font-weight: bold'>Application Insights</div><div style='font-size: 70%; margin-top: 0px'>[Container: Application Insights + Log Analytics]</div><div style='font-size: 80%; margin-top:10px'>Custom metrics (provider_429,<br />notifications_backlog) and<br />exceptions from<br />customer-notifications; the<br />alert rules query it.</div>"]
        style 153 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

      subgraph 155 ["Azure Monitor"]
        style 155 fill:#ffffff,stroke:#444444,color:#444444

        156["<div style='font-weight: bold'>Azure Monitor</div><div style='font-size: 70%; margin-top: 0px'>[Container: Azure Monitor]</div><div style='font-size: 80%; margin-top:10px'>Metric alert rules + action<br />group.</div>"]
        style 156 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 158 ["Anthropic"]
      style 158 fill:#ffffff,stroke:#444444,color:#444444

      159["<div style='font-weight: bold'>Anthropic API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Claude Haiku 4.5, reached<br />through ADK's LiteLLM<br />adapter.</div>"]
      style 159 fill:#8fa1b0,stroke:#64707b,color:#ffffff
    end

    subgraph 161 ["Cloudflare"]
      style 161 fill:#ffffff,stroke:#444444,color:#444444

      162["<div style='font-weight: bold'>NS delegation</div><div style='font-size: 70%; margin-top: 0px'>[Infrastructure Node]</div>"]
      style 162 fill:#ffffff,stroke:#444444,color:#444444
    end

    105-. "<div>enqueue alert id</div><div style='font-size: 70%'></div>" .->113
    113-. "<div>triggers</div><div style='font-size: 70%'></div>" .->106
    107-. "<div>enqueue authorisation</div><div style='font-size: 70%'></div>" .->116
    116-. "<div>triggers</div><div style='font-size: 70%'></div>" .->108
    120-. "<div>notification</div><div style='font-size: 70%'>[SNS subscription]</div>" .->105
    107-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->120
    108-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->120
    109-. "<div>alarm state change</div><div style='font-size: 70%'></div>" .->120
    105-. "<div>put alert</div><div style='font-size: 70%'></div>" .->126
    106-. "<div>read alert + known issues,<br />write verdict</div><div style='font-size: 70%'></div>" .->126
    111-. "<div>query / put</div><div style='font-size: 70%'></div>" .->126
    107-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->130
    108-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->130
    109-. "<div>read fault flag</div><div style='font-size: 70%'></div>" .->130
    111-. "<div>GET/POST/DELETE chaos</div><div style='font-size: 70%'></div>" .->130
    136-. "<div>GET alerts, verdicts; POST<br />known-issue</div><div style='font-size: 70%'>[HTTPS]</div>" .->111
    106-. "<div>read Anthropic key + HMAC<br />secret</div><div style='font-size: 70%'></div>" .->139
    106-. "<div>latency + token metrics</div><div style='font-size: 70%'></div>" .->142
    148-. "<div>GET /chaos (bearer)</div><div style='font-size: 70%'>[HTTPS]</div>" .->111
    150-. "<div>canonical alert</div><div style='font-size: 70%'>[HTTPS + HMAC]</div>" .->105
    148-. "<div>custom metrics</div><div style='font-size: 70%'></div>" .->153
    156-. "<div>action group webhook (common<br />alert schema)</div><div style='font-size: 70%'>[HTTPS]</div>" .->150
    106-. "<div>triage / research / report<br />turns</div><div style='font-size: 70%'>[HTTPS]</div>" .->159

  end
```

## Deployment — where the Kubernetes estate runs (laptop, GitHub Actions)

```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Deployment View: kind"]
    style diagram fill:#ffffff,stroke:#ffffff

    subgraph 163 ["Laptop"]
      style 163 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 164 ["kind cluster"]
        style 164 fill:#ffffff,stroke:#444444,color:#444444

        165["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 165 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        166["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 166 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        167["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 167 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        168["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes the three services'<br />/metrics every 15s; evaluates<br />the six PrometheusRules.</div>"]
        style 168 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        172["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-b-forwarder (webhook).</div>"]
        style 172 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    subgraph 174 ["GitHub Actions runner"]
      style 174 fill:#ffffff,stroke:#444444,color:#444444

      subgraph 175 ["kind cluster"]
        style 175 fill:#ffffff,stroke:#444444,color:#444444

        176["<div style='font-weight: bold'>cards-authorization</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ISO-8583-style auth switch.<br />Chaos: timeouts, issuer-down.</div>"]
        style 176 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        178["<div style='font-weight: bold'>fraud-scoring</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>ML scoring. Chaos:<br />model-drift, latency,<br />crashloop, lag.</div>"]
        style 178 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        180["<div style='font-weight: bold'>open-banking-api</div><div style='font-size: 70%; margin-top: 0px'>[Container: Deployment (Python)]</div><div style='font-size: 80%; margin-top:10px'>PSD2 third-party API gateway.<br />Chaos: rate-limit-storm,<br />cert-expiry.</div>"]
        style 180 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        182["<div style='font-weight: bold'>prometheus</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Scrapes the three services'<br />/metrics every 15s; evaluates<br />the six PrometheusRules.</div>"]
        style 182 fill:#14b8a6,stroke:#0e8074,color:#0e1419
        190["<div style='font-weight: bold'>alertmanager</div><div style='font-size: 70%; margin-top: 0px'>[Container: kube-prometheus-stack]</div><div style='font-size: 80%; margin-top:10px'>Routes firing alerts to<br />route-b-forwarder (webhook).</div>"]
        style 190 fill:#14b8a6,stroke:#0e8074,color:#0e1419
      end

    end

    168-. "<div>scrape</div><div style='font-size: 70%'></div>" .->165
    168-. "<div>scrape</div><div style='font-size: 70%'></div>" .->166
    168-. "<div>scrape</div><div style='font-size: 70%'></div>" .->167
    168-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->172
    168-. "<div>scrape</div><div style='font-size: 70%'></div>" .->176
    168-. "<div>scrape</div><div style='font-size: 70%'></div>" .->178
    168-. "<div>scrape</div><div style='font-size: 70%'></div>" .->180
    182-. "<div>scrape</div><div style='font-size: 70%'></div>" .->165
    182-. "<div>scrape</div><div style='font-size: 70%'></div>" .->166
    182-. "<div>scrape</div><div style='font-size: 70%'></div>" .->167
    182-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->172
    182-. "<div>scrape</div><div style='font-size: 70%'></div>" .->176
    182-. "<div>scrape</div><div style='font-size: 70%'></div>" .->178
    182-. "<div>scrape</div><div style='font-size: 70%'></div>" .->180
    168-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->190
    182-. "<div>firing alerts</div><div style='font-size: 70%'></div>" .->190

  end
```
