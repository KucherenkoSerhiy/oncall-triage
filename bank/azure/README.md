# Azure Function apps

Two Azure Functions apps (Python v2 programming model), each deployed
standalone. This is the M5a slice: the app code, the shared HMAC signer, and
tests. Provisioning them (Terraform: Storage account, Application Insights,
the Consumption plan, zip deploy, Azure Monitor alert rules, the action
group) is M5b (`infra/azure`, documented in `infra/README.md`).

## `customer_notifications/`

Timer trigger `send_batch`, schedule `0 * * * * *` (every minute). "Sends" 20
SMS/e-mail notifications and records custom metrics through Application
Insights (OpenTelemetry). Before each run it polls the console API's
`GET /chaos` route (same control plane the AWS Lambdas use via M4's
`bank-faults` table - Azure can't read that DynamoDB table directly, so it
asks the API instead) and caches the answer for 60 seconds so the timer
never blocks on a slow poll.

| Mode | Behaviour |
| --- | --- |
| normal | `notifications_sent = 20` |
| `provider-429` | `provider_429 = 20`, then raises (drives the Function `Failures` metric) |
| `backlog` | `notifications_sent = 20`, `notifications_backlog = 150`, succeeds |

The logic lives in `notifications.py`, framework-free (no `azure.functions`
import), so it's unit-tested directly - see `tests/bank/azure/`.

## `alert_forwarder/`

HTTP trigger `forward` (route `alerts`, function-key auth, POST). Accepts
either an Azure Monitor **common alert schema** payload (from an action
group) or a Prometheus Alertmanager webhook payload (route B, M6), tells
them apart by shape (`data.essentials` vs. top-level `alerts`), wraps the
payload as `{"source": "azure-monitor" | "alertmanager", "payload": ...}`,
signs it with the same HMAC algorithm the ingest API verifies
(`X-Nordwind-Timestamp`, `X-Nordwind-Signature`), and POSTs it to
`INGEST_URL`. Returns `202` when the ingest API answers 2xx, `502` with the
ingest status otherwise, and logs one JSON line per request.

The logic lives in `forwarder.py`, likewise framework-free.

## `_shared/hmac_sign.py`

A copy of `services/ingest/hmac_auth.py`'s signing algorithm (sign side
only). Each Function app deploys as a standalone zip built from its own
`bank/azure/<app>/` directory plus this `_shared/` folder copied in as a
sibling - the apps never depend on the `services` package, which doesn't
ship with them. `tests/bank/azure/test_hmac_sign.py` pins this copy against
the original so the two never drift.

### The sibling-import trick

Inside a deployed zip, `_shared/` sits right next to `function_app.py`, and
Azure's Python worker adds the app's own directory to `sys.path` before
importing `function_app.py` as a top-level module - so `import _shared...`
(or, within an app, `import notifications` / `import forwarder`) resolves
directly. In the repo (and under pytest) those same files are nested inside
the `bank.azure.*` package instead, so the plain import fails and falls back
to the fully qualified one:

```python
try:
    from _shared.hmac_sign import signed_headers
except ImportError:
    from bank.azure._shared.hmac_sign import signed_headers
```

## Running locally (for the curious)

M5a ships no deployment automation - this is only useful for poking at a
function with the real Functions host installed (`pip install
azure-functions-core-tools`, then `func start` from inside `customer_notifications/`
or `alert_forwarder/`). Set the environment variables below first.

## Environment variables

| App | Variable | Default | Purpose |
| --- | --- | --- | --- |
| `customer_notifications` | `CHAOS_URL` | `https://api.triage.serhiykucherenko.dev/chaos` | Console API chaos route to poll |
| `customer_notifications` | `CONSOLE_TOKEN` | *(none)* | Bearer token for the chaos poll; missing -> normal mode, warns once |
| `alert_forwarder` | `INGEST_URL` | `https://api.triage.serhiykucherenko.dev/alerts` | Ingest API to forward to |
| `alert_forwarder` | `INGEST_HMAC_SECRET` | *(none)* | HMAC secret shared with the ingest API |

Both apps also read `APPLICATIONINSIGHTS_CONNECTION_STRING` when present to
wire up OpenTelemetry export to Application Insights (M5b sets it).

## Why app settings are plaintext (v1)

`CONSOLE_TOKEN` and `INGEST_HMAC_SECRET` are ordinary (non-Key-Vault-backed)
Function app settings, visible in plaintext to anyone with Contributor
access on the resource group - the same posture the AWS Lambdas take with
plain Lambda environment variables. Acceptable for this demo's threat model;
Key Vault references are the M9 hardening upgrade. M5b documents this
trade-off again on the Terraform side (`infra/README.md`).
