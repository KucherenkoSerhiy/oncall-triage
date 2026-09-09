# Console API

Base URL: `$BANKOPS_API` (e.g. `https://api.triage.serhiykucherenko.dev`). All
responses are JSON with `Content-Type: application/json` and CORS headers
(`Access-Control-Allow-Origin: $CONSOLE_ORIGIN`, `Access-Control-Allow-Headers:
Authorization, Content-Type`, `Access-Control-Allow-Methods: GET, POST,
DELETE, OPTIONS`). `OPTIONS` on any route returns `204` with those headers
and requires no auth.

Every route except `GET /health` and `OPTIONS` requires
`Authorization: Bearer $CONSOLE_TOKEN`; a missing or wrong token returns `401`.

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | none | Liveness check |
| GET | `/alerts?limit=` | bearer | Recent `queued`/`triaged` alerts, newest first |
| GET | `/alerts/{alert_id}` | bearer | One alert plus its verdict (or `404`) |
| GET | `/known-issues?service=` | bearer | Known issues, optionally filtered by service |
| POST | `/known-issues` | bearer | Add a known issue |
| DELETE | `/known-issues/{service}/{issue_id}` | bearer | Remove a known issue (`204`/`404`) |
| GET | `/chaos` | bearer | List current bank-estate faults |
| POST | `/chaos/{service}` | bearer | Set a fault (`404` unknown service, `400` invalid mode) |
| DELETE | `/chaos/{service}` | bearer | Clear a fault (`404` unknown service) |

## `GET /health`

```
200 {"ok": true}
```

## `GET /alerts?limit=50`

```
200 [{"alert_id": "...", "service": "payments-api", "status": "queued", "received_at": "...", ...}, ...]
```

## `GET /alerts/{alert_id}`

```
200 {"alert_id": "...", "status": "triaged", ..., "verdict": {"action": "monitor", ...} | null}
404 {"error": "alert not found"}
```

## `GET /known-issues?service=payments-api`

```
200 [{"service": "payments-api", "issue_id": "...", "pattern": "...", "explanation": "...", "taught_by": "console", "created_at": "..."}]
```

## `POST /known-issues`

Request: `{"service": "payments-api", "pattern": "connection pool exhausted", "explanation": "auto-recovers"}`

```
201 {"service": "payments-api", "issue_id": "...", "pattern": "...", "explanation": "...", "taught_by": "console", "created_at": "..."}
400 {"error": "missing fields: ..."}
```

## `DELETE /known-issues/{service}/{issue_id}`

```
204 (no body)
404 {"error": "known issue not found"}
```

## `GET /chaos`

```
200 [{"service": "payments", "mode": "errors", "until": 1234567890, "set_at": 1234567590, "set_by": "console", "active": true}]
```

## `POST /chaos/{service}`

Request: `{"mode": "errors", "minutes": 5}`. `service` is one of `payments`,
`ledger`, `auth`, `customer-notifications`; valid modes: `payments` ->
`errors`, `latency`, `pool`; `ledger` -> `lag`, `reconciliation-mismatch`;
`auth` -> `jwks-rotation`, `lockouts`; `customer-notifications` ->
`provider-429`, `backlog`.

```
201 {"service": "payments", "mode": "errors", "until": 1234567890, "set_at": 1234567590, "set_by": "console"}
400 {"error": "invalid mode 'bogus' for payments; valid modes: errors, latency, pool"}
404 {"error": "unknown service: not-a-service"}
```

## `DELETE /chaos/{service}`

```
204 (no body)
404 {"error": "unknown service: not-a-service"}
```

# `bankops` CLI

`python -m cli.bankops [--api URL] [--hmac-secret S] [--token T] <command> ...`
Flags override `BANKOPS_API`, `BANKOPS_HMAC_SECRET`, `BANKOPS_TOKEN`.

| Command | Purpose |
| --- | --- |
| `fire --service S --alert NAME [--severity sev3] [--title] [--description] [--estate aws] [--label k=v ...] [--log LINE ...]` | POST a signed synthetic alert to `/alerts`; prints `alert_id`/`deduped`, exits `1` on error |
| `tail [--limit N] [--watch] [--interval 10]` | Print a table of recent alerts from `/alerts`; `--watch` repeats until Ctrl-C |
| `teach --service S --pattern P --explanation E` | POST a known issue to `/known-issues` |
| `known [--service S]` | List known issues from `/known-issues` |
| `chaos SERVICE --mode M [--minutes 5]` | POST a fault to `/chaos/{service}`; validates the mode client-side |
| `chaos SERVICE --clear` | DELETE the fault on `/chaos/{service}` |
| `chaos --status` | Print a table of active faults from `/chaos` |
