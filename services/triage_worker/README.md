# Triage worker (M3a)

Runs the three-role ADK triage agent (`oncall_triage/`) per SQS message and
writes the verdict.

## What runs per alert

`lambda_handler` reads `{"alert_id": ...}` off each SQS record, loads the
alert from DynamoDB (missing alert -> failure item, retried by SQS), checks
the daily cap, and calls `TriageRunner.run(alert)`
(`services/triage_worker/runner.py`). That builds a fresh ADK `Runner` and
session (app name `nordwind-triage`), sends `Triage alert <id>: <title>` to
`root_agent`, and collects the final text. Triage calls `get_alert` and
`check_known` (and optionally `get_recent_alerts`), then hands off to
`researcher` (new error) or straight to `reporter` (known error); `reporter`
always produces the final text. The worker writes the verdict, sets the
alert `status` to `triaged`, and logs one JSON line per alert (`alert_id`,
`known`, `action`, `input_tokens`, `output_tokens`, `duration_ms`).

## Verdict contract

`reporter`'s reply must end with a fenced block:

```verdict
{"known": false, "severity": "sev2", "action": "page", "summary": "one line"}
```

`action` is one of `page`, `monitor`, `ack`. `TriageRunner` parses this
block off the end of the text; if it's missing or not valid JSON, the
runner falls back to `{"known": false, "severity": <alert's severity>,
"action": "monitor", "summary": <first 200 chars of the text>}` and sets
`verdict_parse_error=True` on the verdict item, so a bad model reply degrades
to "flag for a human" rather than crashing the batch. The verdict item
written to DynamoDB is `{alert_id, known, severity, action, summary, text,
model, prompt_hash, input_tokens, output_tokens, verdict_parse_error,
created_at}`. Writes are conditional on `attribute_not_exists(alert_id)`,
so SQS redelivery of an already-triaged alert is a no-op.

## Daily cap

`cap.py`'s `DailyCap` keeps one counter item per day in the verdicts table
(`alert_id = "cap#YYYY-MM-DD"`), incremented atomically and conditioned on
staying under `DAILY_ALERT_CAP` (default 500). Once the cap is hit for the
day, the worker skips the model call entirely and writes a verdict with
`action="monitor"`, `model="cap"`, `summary="Daily LLM cap reached; not
triaged"` — the alert is still marked `triaged` so the console shows it
plainly rather than leaving it stuck `queued`.

## Environment variables

`ALERTS_TABLE`, `VERDICTS_TABLE`, `KNOWN_ISSUES_TABLE` (DynamoDB table
names), `ANTHROPIC_API_KEY` (read by LiteLLM, not by this code directly),
`TRIAGE_MODEL` (optional, overrides the default Claude model - see
`oncall_triage/model.py`), `DAILY_ALERT_CAP` (optional, default `500`).

## Testing without a model

Every model interaction goes through one seam: `TriageRunner(agent_factory=...)`.
Tests never construct the default factory (which imports the real,
Claude-backed `root_agent`) - instead they build an agent tree wired to a
scripted `BaseLlm` fake and pass a factory that returns it. See
`tests/triage_worker/fake_llm.py` for the `FakeLlm` class and the
`build_scripted_agent_tree()` / `tool_call_response()` / `text_response()`
helpers, and `tests/triage_worker/test_runner.py` for worked examples
(a known-issue run and a new-issue run, each asserting the real tool
functions were actually invoked by inspecting the fake's recorded
`LlmRequest`s).

## Running the container locally

`task worker:build` builds the image (`Dockerfile`, `public.ecr.aws/lambda/python:3.12`,
arm64) with `oncall_triage/`, `services/ingest/` and `services/triage_worker/`
copied in. `task worker:local` runs it under the Lambda Runtime Interface
Emulator on `localhost:9000` and invokes it with
`tests/triage_worker/fixtures/sqs_event.json`; it needs `ALERTS_TABLE`,
`VERDICTS_TABLE`, `KNOWN_ISSUES_TABLE` and `ANTHROPIC_API_KEY` set in your
shell (pointing at real or local AWS resources) to do anything useful -
the image is never pushed anywhere by either task.

## Decisions taken during implementation

Notes on places where the spec text needed a judgment call to produce a
working system, or where a reasonable default had to be picked.

### `DailyCap.try_acquire(today)` reads the cap from the environment, not an argument

The spec's method signature is literally `try_acquire(today) -> bool` (one
argument), but the condition needs a cap value. `DailyCap.__init__` reads
`DAILY_ALERT_CAP` (default 500) once at construction instead of threading it
through every call. The handler builds a fresh `DailyCap` per invocation, so
this is equivalent to reading it per-call and keeps the method signature
exactly as specified.

### Tool functions never crash on missing data

`tools.get_alert` returns `{"alert_id": ..., "found": False}` instead of
raising when `AlertRepo.get_alert` returns `None`, mirroring the "never
raises, returns a friendly result" style of the M2/phase-1 `get_logs`. In
practice `TriageRunner` always triages an alert the handler already loaded
successfully, so this path is a safety net (e.g. the agent asking about a
different alert_id), not something the happy path exercises.

### Known-issue IDs are `uuid4`, not the ingest pipeline's ULID

`services.console_api.store` reuses `services.ingest.canonical.new_alert_id`
for `issue_id`. `oncall_triage/` intentionally has no dependency on
`services.*` (it's the standalone agent package `adk web` runs), so
`JsonFileStore`/`DynamoStore.add_known` generate `issue_id` with
`uuid.uuid4().hex` instead - same uniqueness guarantee, no cross-package
coupling, and the field is opaque to every caller.

### Tools are (re)configured on every invocation, not memoized at true cold start

`services/triage_worker/handler.py` builds `DynamoStore`/`AlertRepo` fresh
inside `lambda_handler` on every call, matching the M2b stub's existing
pattern of constructing its boto3 resource inside the handler rather than at
module import. This is what makes the handler testable against a fresh
`moto.mock_aws()` per test (a real cold-start cache built at import time
would hold a stale boto3 resource across tests). The cost is negligible -
it only wires lightweight Python objects around table names, no network
call - so the "cold start" framing in the spec is satisfied in spirit
without sacrificing testability.

### Redelivery skips the model, not just the write

`_process_record` first does a cheap `verdicts_table.get_item` and returns
immediately if a verdict already exists, before touching the daily cap or
calling `TriageRunner.run`. An earlier version of this handler mirrored the
M2b stub literally - always running the model, relying only on the
conditional `put_item` to make the write a no-op - on the reading that the
spec's "same conditional put as the stub (redelivery is a no-op)" scoped
the no-op guarantee to the write. That's cheap for the M2b stub (which does
no real work before the write) but not for this handler, where redelivery
would otherwise re-spend a real, billed model call and a cap slot on every
redelivery of an already-triaged alert. The conditional put stays as the
authoritative guard against a concurrent double-write (the existence check
and the put aren't atomic together); the `get_item` is just a short-circuit
for the common sequential-redelivery case.

### `InMemoryAlertsTable`: one boto3-Table-like stand-in, reused everywhere

Rather than giving `AlertRepo` a separate in-memory code path, `InMemoryAlertsTable`
implements the same `get_item`/`put_item`/`query` shape a boto3 `Table`
does. `AlertRepo`'s own logic is then identical whether it's backed by
DynamoDB, moto, or this stand-in - used as `AlertRepo()`'s default (so
`adk web` runs without AWS) and directly in tests that need to seed alerts
without a moto table.

### Dockerfile copies only what the spec lists

`services/__init__.py` is not copied (the spec names `oncall_triage/`,
`services/ingest/`, `services/triage_worker/` only) - Python 3.3+'s implicit
namespace packages make `services` importable as a package without it, so
`services.triage_worker.handler.lambda_handler` still resolves inside the
image.

### `docs/agent.md`'s local walkthrough was updated, not just `docs/agent.md`'s new section

The spec only asks for a "phase 2" pointer paragraph, but the existing
`adk web` walkthrough text was factually wrong after this milestone's
changes: it referenced `GOOGLE_API_KEY` (the model is now Claude via
LiteLLM, which reads `ANTHROPIC_API_KEY`) and prompts like "check
payments-service logs" (the `get_logs(service)` tool no longer exists -
triage now works off `get_alert(alert_id)`, and the default local
`AlertRepo` starts empty). Left as-is, the walkthrough would no longer
work; both were corrected alongside the required new section.
