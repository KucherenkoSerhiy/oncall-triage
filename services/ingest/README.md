# Alert ingest (M2a)

Turns alerts from four sources into one canonical shape, scrubs PII, and
de-duplicates before handing off to the triage queue.

## Event shapes handled by `lambda_handler`

1. **HTTP** — API Gateway HTTP API v2 `POST /alerts`, body
   `{"source": "<bankops|cloudwatch|alertmanager|azure-monitor>", "payload": {...}}`,
   headers `x-nordwind-timestamp` / `x-nordwind-signature` (HMAC, below).
   Returns `202 {"results": [{"alert_id", "fingerprint", "deduped"}]}`,
   `401` on a bad signature, `400` on malformed JSON/unknown source, `422`
   when the payload isn't a firing alert (e.g. a resolved alert).
2. **SNS** — a native SNS event (`Records[].Sns.Message`), always
   `cloudwatch`; no HMAC, the SNS subscription is the trust boundary.
   Returns `{"results": [...]}` directly. Non-`ALARM` states (`OK`,
   `INSUFFICIENT_DATA`) produce no result and are skipped.

## Canonical alert

`CanonicalAlert` (`canonical.py`): `alert_id` (26-char ULID), `fingerprint`,
`source`, `estate`, `service`, `alert_name`, `severity` (`sev1`-`sev4`),
`title`, `description`, `sample_logs`, `labels`, `fired_at`/`received_at`
(RFC 3339 UTC), `raw`. `fingerprint` is a sha256 of source/service/alert_name
plus sorted labels, excluding `route`, `runbook` and any `_`-prefixed label.

## HMAC header contract

`x-nordwind-signature: sha256=<hex>`, where `<hex>` is
`HMAC-SHA256(secret, timestamp + "." + raw_body)`; `x-nordwind-timestamp`
is epoch seconds, checked against a 300s skew window.

Worked example — secret `s3cr3t`, timestamp `1700000000`, body
`{"hello":"world"}`:

```
x-nordwind-timestamp: 1700000000
x-nordwind-signature: sha256=50e72260c1914d42209776f3128a2921bd83fb959b1e03eabaa411d4ca82c6a9
```

## Dedup rule

An alert is deduped against the most recent alert with the same
`fingerprint`, `status` `queued`/`triaged`, and `received_at` within the
last 30 minutes: a match bumps `occurrences` and skips the queue; no match
stores a new item (`status=queued`, `occurrences=1`) and sends
`{"alert_id": ...}` to SQS.

## Environment variables

`ALERTS_TABLE` (DynamoDB table name), `ALERTS_QUEUE_URL` (SQS queue URL
for newly-queued alerts), `INGEST_HMAC_SECRET` (shared secret, HTTP path
only).

## Running the tests

`pytest tests/ingest` — uses `moto`'s `mock_aws` to fake DynamoDB (table +
`by_fingerprint` GSI) and SQS; no AWS account or credentials needed.

## Decisions taken during implementation

The spec left a handful of details open. Choices made, and why:

- `CanonicalAlert.labels`, `fired_at`, `received_at`, `raw` have default
  values (`{}`, `""`, `""`, `{}`). Every adapter always fills them
  explicitly; the defaults just make ad-hoc construction (tests) less
  verbose and don't change validation, which still runs in `__post_init__`
  regardless of how the instance was built.
- `cloudwatch` adapter: `description` is set to the alarm's
  `AlarmDescription` (title already combines `AlarmName` + `NewStateReason`
  per spec). `labels` is populated from `Trigger.Dimensions` (`name -> value`)
  since that's the only source-specific context available and it feeds the
  fingerprint/log context like other adapters' labels do.
- `azure_monitor` adapter: `title` is the bare `alertRule` name (spec fixes
  `alert_name` to the same value but doesn't define `title` explicitly);
  `description` is `data.essentials.description`. No labels are extracted
  since the schema doesn't expose a label-like map (`alertContext` is kept
  in `raw` instead, as specified). `service` falls back to `"unknown"` if
  `alertTargetIDs` is empty, mirroring the cloudwatch adapter's fallback.
- `handler.py`: an HTTP request naming a `source` outside the four known
  adapters gets `400` (treated as a `ValueError` naming the field, same
  status class as other malformed-input cases). Within one SNS batch, a
  record whose CloudWatch state isn't `ALARM` (`NotAnAlert`) is skipped
  rather than failing the whole batch — SNS delivers OK/INSUFFICIENT_DATA
  transitions too and those aren't errors.
- Structured logging is one `logger.info(json.dumps({...}))` call per
  alert; no custom log formatter is configured (out of scope — the spec
  only requires the fields to be present in the line).
