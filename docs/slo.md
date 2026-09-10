# SLO: verdict latency

**95% of alerts receive a verdict within 5 minutes of arrival**, measured
daily from the alert's `received_at` (ingest's write to the `alerts` table)
to its verdict's `created_at` (the triage worker's write to the `verdicts`
table).

## What counts

- **Every estate.** An alert from AWS (CloudWatch alarm), Azure (Azure
  Monitor rule via the forwarder), Kubernetes (route A over Kafka or route
  B via the forwarder), or `bankops fire` is measured the same way — the
  SLO is about the triage brain's own latency, not where the alert came
  from.
- **Known-issue short-circuits count as verdicts.** `check_known` matching
  and returning immediately (no researcher/reporter turn) is still a real
  triage outcome — fast is the point.
- **Cap short-circuits count as misses**, regardless of measured latency.
  When `services/triage_worker/cap.py`'s daily counter is exhausted, the
  worker writes a placeholder verdict (`model = "cap"`, "Daily LLM cap
  reached; not triaged") in well under 5 minutes — but that alert never
  received a real triage, so it is excluded from the "hit" count `slo-
  reporter` uses to compute attainment even though its raw latency would
  otherwise pass. It still contributes to `VerdictLatencyP95`, which is a
  latency measurement, not an SLO-compliance judgement — see
  `bank/ops/slo_reporter/handler.py`.
- An alert that never gets a verdict at all (stuck in the DLQ, or awaiting
  redelivery past the reporting window) is simply not in the "alerts with
  a verdict" set `slo-reporter` reads the next day — it doesn't inflate
  either the hit or the miss count; the `AlertsDlqDepth` ops alarm
  (`infra/aws/observability.tf`) is what catches that failure mode instead.

## Error budget

Over a rolling 30-day window, up to **5% of alerts** may miss the
5-minute target before the SLO is considered breached. Expressed against
`var.daily_alert_cap` (500 alerts/day, the worst-case ceiling the daily
LLM cap enforces — see `docs/DESIGN.md` section 9, "Cost model"), that is
30 × 500 × 5% = **750 missed verdicts allowed per month** (an average of
25/day) before the budget is exhausted. In practice this project's actual
volume is a small, bursty fraction of the cap — synthetic traffic from
`bankops fire`, the AWS/Azure/Kubernetes chaos scenarios, and the three
bank estates' scheduled Lambdas, not continuous production load — so a
single miss on a quiet day already shows up as a visible dip in
`SloAttainment`. The dashboard's SLO widget (below), not the raw miss
count, is the signal worth watching day to day.

## How it's measured

`bank/ops/slo_reporter/handler.py`, an AWS Lambda on a daily EventBridge
schedule (`cron(15 0 * * ? *)`, 00:15 UTC — 15 minutes after midnight so
the previous UTC day's alerts have finished draining the queue), reads
yesterday's triaged alerts (the `alerts` table's `by_status` GSI) and
their verdicts, and publishes three custom metrics under `Nordwind/Triage`
(dimension `estate=all`, so each is one time series):

| Metric | What |
|---|---|
| `VerdictLatencyP95` | p95 of `verdict.created_at - alert.received_at`, in seconds, over every triaged alert with a verdict |
| `AlertsTriaged` | count of alerts triaged that day |
| `SloAttainment` | fraction of those alerts that both weren't a cap short-circuit and had latency <= 300s |

It also logs one JSON line per run: `{"day", "alerts", "p95_seconds",
"attainment"}` — CloudWatch Logs Insights-queryable, and what the
`diagnose.yml` workflow's dashboard/alarm step points an operator at.

## Where it shows

The `nordwind-triage-demo` CloudWatch dashboard (`infra/aws/observability.tf`)
has a widget plotting `VerdictLatencyP95` and `CapReached` against
`SloAttainment`, with a horizontal annotation at 0.95 marking the target —
attainment dipping below the line is visible at a glance, before it shows
up as an `ops-CapReached` or `ops-WorkerDurationP95` alarm.
