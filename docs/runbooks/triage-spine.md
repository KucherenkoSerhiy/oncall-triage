# Runbook: the triage spine

The spine is `ingest` &rarr; SQS `alerts` queue &rarr; `triage-worker` &rarr;
DynamoDB (`alerts`, `verdicts`, `known-issues`) &rarr; `console-api` &rarr;
the incident console - the AWS-hosted brain every estate feeds (see
`docs/DESIGN.md` §5 for the sequence diagram). This runbook is symptom-first:
find what you're seeing, run the one `diagnose.yml` invocation named for it,
read the section it tells you to, apply the fix, confirm the verify step.
Every "likely causes" entry cites the issue that incident was fixed under -
see [ADR 0017](../adr/0017-runbooks-derived-from-incidents.md) for why.

`gh workflow run diagnose.yml` is the read-only tool throughout: Actions ->
diagnose -> Run workflow also works with no `gh` installed. Every run needs
no laptop credential - it assumes the same OIDC deploy role `deploy.yml`
uses. `docs/slo.md` and the CloudWatch dashboard
(`https://eu-north-1.console.aws.amazon.com/cloudwatch/home?region=eu-north-1#dashboards:name=nordwind-triage-demo`)
are worth a look before any of the sections below - `diagnose.yml`'s first
step prints the same dashboard link and the five `ops` alarm states.

## Ingest 5xx / 422s

**What you see**: `scripts/smoke.py` fails with `FAIL[fire-alert]: HTTP 5xx:
...` or `FAIL[fire-alert]: HTTP 422: ...`; API Gateway access logs show the
same; the CloudWatch dashboard's ingest `Errors` widget ticks up.

**First check**:

```bash
gh workflow run diagnose.yml -f minutes=30 -f log_lines=60
```

Read "Newest worker + ingest log lines" (`/aws/lambda/nordwind-triage-demo-ingest`)
for the stack trace, and "Lambda metrics" for `ingest`'s `Errors` count.

**Likely causes**:

- **5xx - an unhandled exception in `services/ingest/handler.py`.** The
  first live alarm crashed ingest exactly this way: a real CloudWatch alarm
  message carries floats (`Trigger.Threshold: 1.0`, ...) inside its raw
  payload, and `boto3`'s DynamoDB client refuses Python floats outright
  ([#50](https://github.com/KucherenkoSerhiy/oncall-triage/issues/50), fixed
  by a JSON round-trip with `parse_float=Decimal` in
  `services/ingest/canonical.py`). Any *new* adapter or payload shape that
  round-trips through `json.loads` without `parse_float=Decimal` can
  reintroduce the same crash - check the log line names the offending field.
- **422 - `NotAnAlert`**: an Alertmanager batch with no firing alerts (every
  alert in the webhook had already resolved) - not itself an incident,
  `services/ingest/handler.py`'s `_alerts_for` raises it on purpose. Frequent
  422s from the same route point at Alertmanager's `group_wait`/`resolve`
  timing rather than ingest.
- **401** (the sibling status this same log will show): the HMAC signature
  failed - see "Console 401s" below for the token-rotation case, or check
  whether `INGEST_HMAC_SECRET` was rotated in one place (SSM) but not yet
  re-read by the caller (forwarder app setting, `kafka-relay` Secret) - see
  [`docs/runbooks/secrets-rotation.md`](secrets-rotation.md).

**Fix**: for a genuinely new payload shape, the fix is a code change (patch
the adapter, add a test fixture from the real payload, redeploy). For 422
noise, no fix is needed - it's `ingest` behaving correctly.

**Verify**: `python scripts/smoke.py` (or `python scripts/chaos_probe.py
--service <service> --mode <mode> --expect-alert <name>`) completes with
`OK: alert_id=...`.

## An alert silently disappears (dedup collision)

**What you see**: `POST /alerts` (or `bankops fire`) returns HTTP 202 -
no error, nothing to alarm on - but there's no new row on the console and
no new verdict; instead an *existing* alert's `occurrences` count goes up
by one and its `last_seen_at` moves forward. The fire/probe response body
itself gives it away: `{"alert_id": "<the older alert's id>", "deduped":
true}` instead of a fresh `alert_id` with `"deduped": false`.

**First check**:

```bash
gh workflow run diagnose.yml -f alert_id=<the alert_id the fire/probe response returned>
```

read the "Alert record" section - if `occurrences` is greater than 1 and
`received_at` predates when you actually fired, this alert absorbed your
new one rather than creating it.

**Likely cause**: `services/ingest/dedup.py`'s `AlertStore` dedups on
`fingerprint` (`sha256(source, service, alert_name, labels)`) within a
**30-minute window** (`_DEDUP_WINDOW`, `by_fingerprint` GSI) - a real
alarm still flapping bumps the same open alert on purpose (so a flapping
alarm can't burn the LLM budget), but the exact same mechanism silently
absorbed two *unrelated* firings that happened to share a fingerprint:

- **The deploy-time smoke probe** (`scripts/smoke.py`) always fires
  `source=bankops, service=smoke, alert_name=SmokeTest` with no
  distinguishing label - two `deploy.yml` runs inside the same 30-minute
  window produced identical fingerprints, so the second smoke alert was
  absorbed into the first: never queued, never triaged, and the second
  deploy's smoke step had nothing to poll a verdict for
  ([#38](https://github.com/KucherenkoSerhiy/oncall-triage/issues/38)).
- **Two `estate-demo.yml` runs close together** hit the identical failure
  from the Kubernetes side: Prometheus's alert labels (service, alert
  name) don't vary run to run, so a scheduled run following a manual
  dispatch within 30 minutes (or two manual re-dispatches) shared a
  fingerprint with the prior run's still-open alert and the second run's
  alert was absorbed the same way
  ([#71](https://github.com/KucherenkoSerhiy/oncall-triage/issues/71)).

**Fix**: give each firing instance a fingerprint-distinguishing label
instead of touching the dedup window itself (30 minutes is deliberate -
see "Worker cap reached" above). `scripts/smoke.py`'s `probe_run_id()`
puts `labels.probe_run` (the `GITHUB_RUN_ID`, or a timestamp locally) on
every fired alert so consecutive smoke probes never collide; estate-demo's
Alertmanager config carries a per-run `cluster` external label
(`DEMO_RUN_ID`, `scripts/render_alertmanager_values.py`) for the same
reason. Firing manually with `bankops fire` inside another alert's
30-minute window: pass a distinguishing `--label` (e.g. `--label
run=$(date +%s)`).

**Verify**: the fire/probe response shows `"deduped": false` and a fresh
`alert_id`; `GET /alerts/{alert_id}` for that new id returns a verdict of
its own rather than 404 (nonexistent) or someone else's older record.

## Queue backing up

**What you see**: the dashboard's SQS age widget climbs; `ops-WorkerErrors`
or `ops-WorkerDurationP95` may also be firing; the console's alert list
shows a growing number of `status=queued` rows that never flip to
`triaged`.

**First check**:

```bash
gh workflow run diagnose.yml -f minutes=30
```

Read "Queues (visible / in flight / DLQ)" for the `alerts` queue's
`ApproximateNumberOfMessages*`, and "Account concurrency + worker
configuration" for the worker's `State`/`LastUpdateStatus` and the
account's `ConcurrentExecutions` ceiling.

**Likely causes**: the worker is throttled (account concurrency exhausted -
rare at this demo's volume, but a stuck rollback or a runaway chaos loop can
get there), or every invocation is failing before it acks the SQS message
(check "Newest worker + ingest log lines" for a repeating exception - Claude
API errors, a `ClientError` from DynamoDB, or a bad `ANTHROPIC_API_KEY`
after a rotation that didn't sync - see
[`docs/runbooks/secrets-rotation.md`](secrets-rotation.md#anthropic-api-key)).

**Fix**: a throttled worker clears itself once the offending load stops
(`bankops chaos --status` to find and clear a fault left running past its
`--minutes`). A consistently-failing worker needs the underlying error
fixed; in the meantime the queue's `maxReceiveCount` (3) moves poison
messages to the DLQ automatically - see the next section.

**Verify**: the queue's `ApproximateNumberOfMessages` returns to ~0 and
`bankops tail --watch` shows `status` flipping to `triaged` again.

## DLQ depth alarm (`ops-AlertsDlqDepth`)

**What you see**: an e-mail from the `ops` SNS topic, or `diagnose.yml`'s
first step showing `ALARM` for `nordwind-triage-demo-ops-AlertsDlqDepth`.
One or more alerts failed the worker three times running
(`messaging.tf`'s `maxReceiveCount`) and now sit on `alerts-dlq`, untried.

**First check**:

```bash
gh workflow run diagnose.yml -f minutes=60 -f replay_dlq_max=0
```

Read "Queues" for the DLQ's message count, and "Newest worker + ingest log
lines" for what the three failed attempts logged - that log line is why the
message is poison, and should be understood before replaying it blindly
into the same failure three more times.

**Likely causes**: the same exhaustive list as "queue backing up" above -
most often a payload shape ingest normalised successfully but the worker's
tools choke on (a malformed `known-issues` entry, an alert missing a field
the prompt template assumes).

**Fix**: once the underlying cause is understood (and, if it was a code bug,
fixed and deployed), replay from the DLQ - this is M9b's operator path, no
laptop AWS credential needed:

```bash
gh workflow run diagnose.yml -f replay_dlq_max=10
```

which runs `bankops replay-dlq --max 10 --yes` with the deploy role. Locally,
with `BANKOPS_ALERTS_QUEUE_URL`/`BANKOPS_ALERTS_DLQ_URL` exported (see
`infra/README.md`'s "Poison messages" section): `python -m cli.bankops
replay-dlq --yes`.

**Verify**: `ops-AlertsDlqDepth` returns to `OK`; the replayed alert's
`alert_id` (printed by the replay command) shows a verdict via `GET
/alerts/{alert_id}`.

## Worker cap reached (`ops-CapReached`)

**What you see**: `Nordwind/Triage`'s `CapReached` metric fires the
`ops-CapReached` alarm; verdicts start coming back with `verdict.model ==
"cap"` instead of a real Claude model id - `scripts/smoke.py` and
`scripts/chaos_probe.py` both treat that as a hard failure (`expected a real
model, got 'cap'`).

**First check**:

```bash
gh workflow run diagnose.yml
```

Read "Daily LLM cap counter (alerts table, key cap#\<utc date\>)" - the item
under today's date is the running count against `var.daily_alert_cap`
(default 500/day).

**Likely causes**: a flapping fault left running (chaos with `--minutes`
much longer than intended, or a fault never cleared - `bankops chaos
--status` lists every active one) driving far more distinct alerts than a
normal demo day; fingerprint dedup (30-minute window) caps *repeat* alerts
but not *distinct* ones, so a chaos mode that varies its alert name or
labels per firing bypasses it entirely.

**Fix**: clear the fault (`bankops chaos <service> --clear`, or `task
chaos-k8s -- <service> clear` for Kubernetes); the cap resets at UTC
midnight (`cap#<date>` is a new DynamoDB item every day) - there is no
manual reset short of raising `var.daily_alert_cap` and redeploying, which
is not something to do reflexively.

**Verify**: the next alert's verdict shows a real `model` id (not `"cap"`
or `"stub"`).

## Verdicts missing (console shows "pending" forever)

**What you see**: an alert's `status` reaches `triaged` (via `bankops tail`
or `diagnose.yml`'s "Alert record" step), but the incident console still
shows it "pending", and `bankops tail`'s VERDICT column stays `-`.

**First check**:

```bash
gh workflow run diagnose.yml -f alert_id=<alert_id>
```

read the "Alert record" section's `status` field, then compare against
`GET /alerts/{alert_id}` (bearer token required) rather than `GET /alerts`.

**Likely cause**: `services/console_api/store.py`'s `list_alerts` - what
both the console and `bankops tail` call - queries the `alerts` table only
and never joins the `verdicts` table; only `get_alert` (one alert by id)
does. This is the same gap `scripts/estate_scenarios.py` hit in the first
Kubernetes demo, which waited the full 10-minute timeout on a verdict that
had actually landed after 15 seconds because it was polling the list
endpoint
([#68](https://github.com/KucherenkoSerhiy/oncall-triage/issues/68)) - the
scenario script and the smoke/chaos probes were fixed to poll `GET
/alerts/{id}`, but the console's own list view still renders `alert.verdict`
straight from the list response and therefore still shows every alert
"pending" regardless of its real status.

**Fix**: there isn't one at the list-view level in this milestone - it's a
known limitation, not a live incident. Click into the alert (or hit `GET
/alerts/{alert_id}` directly) to see the real verdict; `bankops tail` has
the same limitation as the console for the same reason.

**Verify**: `GET /alerts/{alert_id}` returns a non-null `verdict` with a
real `model` id.

## An estate's alert never arrives

Symptom in every case: a fault is set (`bankops chaos` / `task chaos-k8s`),
`bankops chaos --status` (or `task estate-status`) confirms it's active, but
no alert shows up on the spine within the expected window. Work backwards
along the path for the estate in question - **the failure is almost always
one hop before ingest**, so `diagnose.yml` (which only sees ingest onward)
won't show anything wrong; check the estate's own alarm/console first.

### AWS: CloudWatch alarm -> SNS -> ingest

**First check**: `gh workflow run diagnose.yml -f minutes=30` - "Bank estate
- active faults, alarm states + history, SNS delivery" prints the alarm's
current state and history, and the `alarms` SNS topic's delivery metrics
(`NumberOfNotificationsDelivered` vs `NumberOfNotificationsFailed`).

**Likely cause**: the `alarms` SNS topic is deliberately **not**
KMS-encrypted - CloudWatch alarms cannot publish to a topic encrypted with
the AWS-managed key `alias/aws/sns` (its key policy doesn't grant
`cloudwatch.amazonaws.com` publish rights), which silently dropped every
alarm notification in M4's first live probe
([#47](https://github.com/KucherenkoSerhiy/oncall-triage/issues/47)) - the
alarm itself showed `ALARM` in the console the whole time, nothing ever
reached ingest, and nothing errored anywhere. If this ever regresses (a
customer-managed KMS key added to `aws_sns_topic.alarms` without also
updating its key policy), the symptom is identical: alarm fires, delivery
count stays 0, no error.

**Fix**: confirm `infra/aws/messaging.tf`'s `aws_sns_topic.alarms` has no
`kms_master_key_id` (or, if a CMK is ever added, that the key policy grants
`cloudwatch.amazonaws.com`). This is a Terraform-level fix, not an operator
action.

**Verify**: `NumberOfNotificationsFailed` stays 0 across the next chaos
probe; `python scripts/chaos_probe.py --service payments --mode pool
--expect-alert PoolExhausted --expect-known` reaches a verdict.

### Azure: Azure Monitor -> action group -> forwarder

**First check**: the Azure Functions log stream (`az functionapp log tail
-n nordwind-triage-demo-forwarder -g rg-nordwind-triage-demo`) or Log
Analytics; `gh workflow run diagnose.yml` doesn't reach into Azure, but its
"Bank Lambda log lines" step is the AWS-side confirmation nothing ever
arrived.

**Likely causes**:

- **The Function app deployed but indexed no functions** - a zip deploy can
  "succeed" while Oryx's remote build never ran, leaving the timer/HTTP
  triggers missing entirely. `WEBSITE_RUN_FROM_PACKAGE=1` skips that build
  and left `azure-monitor-opentelemetry` missing, so the worker couldn't
  even index the app
  ([#59](https://github.com/KucherenkoSerhiy/oncall-triage/issues/59)); more
  generally, any content problem that leaves an app functionless surfaces
  the same way ([#64](https://github.com/KucherenkoSerhiy/oncall-triage/issues/64)).
  `deploy.yml`'s apply leg now has a "Verify the Function apps indexed
  their functions" step that fails the deploy itself on this, so a live
  demo hitting this means that guard was bypassed or the app was changed
  outside Terraform.
- **The alert rule's own schema is wrong for the metric/table it targets** -
  `exceptions/count` only accepts the `Count` aggregation
  ([#57](https://github.com/KucherenkoSerhiy/oncall-triage/issues/57)), and
  a `scheduled_query_rules_alert_v2` log rule needs a named numeric column
  (`metric_measure_column`) over the `AppMetrics` table, not the classic
  `customMetrics` schema - both fixed in `infra/azure/alerts.tf`, both fail
  silently (rule saves, never fires) rather than with an error if reverted.
- **The alert reached the forwarder but ingest rejected it as the wrong
  service** - `services/ingest/adapters/azure_monitor.py` originally trusted
  the alert's `alertTargetIDs`, which for these rules is the Application
  Insights component or the Log Analytics workspace, never the bank service
  itself; the adapter now regexes `service=<name>` out of the rule's
  `description` instead
  ([#66](https://github.com/KucherenkoSerhiy/oncall-triage/issues/66)). A
  new alert rule that omits `service=...; ...` from its description will
  reach ingest but attribute to the wrong (or no) service.

**Fix**: for the first, redeploy `infra/azure` and re-check with
`az functionapp function list`; for the second and third, the fix is a
Terraform/adapter change already in place - a regression means one of those
got reverted or a new rule was added without the `service=` convention.

**Verify**: `gh workflow run deploy.yml -f root=azure -f
chaos_probe=notifications-429` (or manually: `bankops chaos
customer-notifications --mode provider-429`) reaches a verdict within
~5-7 minutes.

### Kubernetes: Alertmanager -> route A relay / route B forwarder

**First check**: `task estate-status` (firing alerts, faults, pods) and, for
route A specifically, `kubectl -n bank logs deploy/kafka-relay --tail=200`
- retry/backoff and `relay_dropped_total` show up there first. In CI,
`estate-demo.yml`'s uploaded artifacts (`alertmanager-alerts.json`,
`prometheus-rules.json`, `kafka-relay.log`, `events.txt`) cover the same
ground for a run that already tore its cluster down - see
[`docs/runbooks/kubernetes-estate.md`](kubernetes-estate.md#reading-estate-demo-artifacts).

**Likely causes**:

- **The rule never left `pending`, or never left `inactive`** - a metrics
  problem on the service side, not delivery; check the service's `/metrics`
  before suspecting Alertmanager.
- **`kafka-relay` posted a bare Alertmanager payload** - ingest expects an
  envelope, `{"source": "alertmanager", "payload": {...}}`, and rejects
  anything else with a 400; the very first route-A demo sent the raw
  Alertmanager webhook body and every alert bounced
  ([#86](https://github.com/KucherenkoSerhiy/oncall-triage/issues/86)) -
  `bank/k8s/kafka_relay/service.py` wraps it correctly now, but a
  hand-rolled test message posted straight to the topic will hit the same
  400 if it skips the envelope.
- **Kafka itself, or the estate's supporting pods, aren't up** - the
  `nordwind-bank` chart's install intentionally doesn't `--wait` on the
  bank namespace (service pods mount `KafkaUser` Secrets that only exist
  once Strimzi is ready, so a chart-level wait would time out on
  `ContainerCreating`
  ([#75](https://github.com/KucherenkoSerhiy/oncall-triage/issues/75))),
  and on a 4-vCPU GitHub runner the Strimzi cluster operator itself
  crash-loops if CPU-limited while reconciling
  ([#83](https://github.com/KucherenkoSerhiy/oncall-triage/issues/83)) -
  `deploy/helm/values/strimzi.yaml` gives it memory but no CPU limit for
  exactly this reason. `task estate-status -- --kafka` shows consumer lag
  per group; a broker that never came `Ready` is the `broker-down` chaos
  action itself, not an incident - see
  [`docs/runbooks/kubernetes-estate.md`](kubernetes-estate.md#broker-down-recovery)
  ([#78](https://github.com/KucherenkoSerhiy/oncall-triage/issues/78)).
- **The alert took the wrong route** - every canonical alert carries
  `labels.route` (`"A"` or `"B"`); an alert that should have gone over
  Kafka but shows `route=B` (or vice versa) means Alertmanager's static
  receiver match sent it down the wrong path, not a delivery failure - check
  `deploy/helm/values/kube-prometheus-stack.yaml`'s route config, not the
  relay/forwarder.

**Fix**: match the specific cause above; for anything Kafka/Strimzi-shaped,
`docs/runbooks/kubernetes-estate.md` is the deeper reference.

**Verify**: `python scripts/estate_scenarios.py --scenario fraud-lag`
(route A) or `--scenario broker-down` (route B) passes, including its
`labels.route` assertion.

## Console 401s (token rotation)

**What you see**: the console shows a login-style error, or every
`GET`/`POST` from the browser gets HTTP 401; `bankops` commands fail with
`error: {"error": "..."}`  from the console API.

**First check**: confirm whether the console token was recently rotated -
see [`docs/runbooks/secrets-rotation.md`](secrets-rotation.md#console-token)
- rotation is a `random_password.console_token` Terraform recreate, and
every existing bearer (browser localStorage, a `bankops` config, the
notifications Function's `CONSOLE_TOKEN` app setting) keeps the *old* value
until it's refreshed by hand.

**Likely cause**: `services/console_api/handler.py`'s `check_bearer`
compares the request's `Authorization: Bearer <token>` against
`CONSOLE_TOKEN`, read from SSM at deploy time - once `infra/aws` applies a
rotation, every caller still holding the previous value gets 401 until it
re-reads the new one. This is expected, not a bug - ADR
[0010](../adr/0010-console-auth-bearer-token.md) accepted exactly this
trade-off ("the token is rotated by re-applying Terraform").

**Fix**: fetch the current value and update every reader:

```bash
aws ssm get-parameter --with-decryption \
  --name /nordwind-triage/demo/console-token --query Parameter.Value --output text
```

then the console's **Change token** button (top of the page), any local
`bankops` config/env var, and - if the notifications Function still 401s
calling the console API's `/chaos` route after its own redeploy - confirm
`infra/azure` was applied after `infra/aws` so it picked up the new value
via the `-var=console_token=...` plan/apply flag.

**Verify**: the console loads the alert list without a 401; `bankops tail`
succeeds.
