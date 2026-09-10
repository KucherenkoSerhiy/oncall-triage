# Runbook: cost

Where every dollar goes, the two guardrails, what always-free covers, what
to destroy first if a budget alarm fires, and a checklist for a month after
this repository goes live. The table below is `docs/DESIGN.md` §9's cost
model, refreshed against what's actually deployed today - no Cost Explorer
or Cost Management screenshots (per the spec for this runbook: numbers, not
pictures), but see "Reconciling against real billing" for why the numbers
here are the *model*, not a pulled invoice total, and what to do about that
gap.

## Where each dollar goes

| Line | Meter | Live today? | $/month |
|---|---|---|---|
| Lambda (ingest, worker, API, 3 AWS bank services, `slo-reporter`, `known-issues-export`) | requests + GB-s | yes | 0 |
| SQS, SNS, EventBridge | per message | yes | 0 |
| DynamoDB (3 core tables + `bank-faults`) | provisioned units + GB | yes (provisioned, not on-demand - on-demand is *not* free) | 0 |
| CloudWatch alarms | per alarm beyond the always-free 10 | yes - 11 (6 bank `alarms.tf` + 5 `ops` `observability.tf`), 1 over free | 0.10 |
| CloudWatch custom metrics | per metric beyond the always-free 10 | yes - 8 (4 `Nordwind/Bank` + 4 `Nordwind/Triage`), inside free | 0 |
| CloudWatch Logs (DNS query log group, 7-day retention) | GB ingested | yes, negligible volume | ~0 |
| API Gateway HTTP API | per million calls | yes, well under 100k/month | ~0.10 |
| S3 + CloudFront (console) | GB stored + egress | yes; console < 1 MB, 1 TB egress always-free | ~0.05 |
| S3 (known-issues weekly export, 30-day lifecycle) | GB stored | yes, cents-scale JSON, self-expiring | ~0 |
| ECR (worker image) | GB-month stored | yes, one ~700 MB image, lifecycle keeps last 10 | ~0.07 |
| SSM Parameter Store (3 SecureStrings) | free standard tier | yes | 0 |
| AWS Budgets | per budget | yes, 1 (first two free) | 0 |
| Azure Functions (forwarder + notifications) | executions + GB-s | yes, well under 100k/month | 0 |
| Azure Storage account | GB + transactions | yes, required Functions companion | ~0.20 |
| Application Insights / Log Analytics | GB ingested (5 GB free; `daily_quota_gb=0.2` caps it) | yes | 0 |
| Azure Monitor alert rules | per rule / time series | yes, 3 rules (10 series free) | ~0.10 |
| Route 53 hosted zone + ACM | per zone-month; ACM free | yes | 0.50 |
| **KMS asymmetric key (DNSSEC signing)** | per key-month | **no** - `enable_dnssec` defaults `false` and no deploy passes `-var=enable_dnssec=true` yet (infra/README.md "DNSSEC") | 0 today, ~1.00 once enabled |
| GitHub Actions minutes | per minute beyond 2,000 free/month (private) | n/a - repo is public (unlimited) | 0 |
| Kubernetes (kind) | laptop / GitHub Actions runner | yes | 0 |
| **Cloud total** | | | **≈ 0.80-1.00 today; ≈ 1.80-2.00 once DNSSEC signing is turned on** |
| Anthropic API *(outside the cloud budgets)* | per MTok in/out, Haiku 4.5 $1/$5 | yes | ≈ 2.50 at the modelled 300 alerts/month |

This is the model kept current as resources are added (M9a's dashboard/ops
alarms, M9b's export bucket, M9c's DNSSEC key and query-log group), not a
pulled invoice - see "Reconciling against real billing" below for why, and
what closes that gap.

## The two budgets

One e-mail address for both - the `BUDGET_EMAIL` GitHub Environment secret,
passed to both roots as `-var="notification_email=..."` in every
`deploy.yml` plan/apply step:

| Budget | Root | Threshold | Notifications |
|---|---|---|---|
| `nordwind-triage-demo-monthly` | `infra/aws` (`aws_budgets_budget`, `main.tf`) | $8/month | 80% actual, 100% forecasted, both to `notification_email` |
| `nordwind-triage-demo-monthly` | `infra/azure` (`azurerm_consumption_budget_resource_group`, `main.tf`) | $2/month | 80% actual, 100% forecasted, both to `notification_email` |

$10 combined, matching `docs/DESIGN.md`'s "Cloud spend target ≤ $10/month"
- split $8/$2 because the AWS side (the triage brain plus three bank
services) is genuinely the larger footprint; Anthropic spend is billed
separately and neither budget covers it (there is no AWS/Azure resource to
attach a budget to - the daily alert cap, `services/triage_worker`'s
`DailyCap`, is the guardrail there instead, with its own `ops-CapReached`
alarm - see `docs/runbooks/triage-spine.md`).

## What the always-free tiers cover

Lambda (1M requests + 400,000 GB-s/month, always-free, not the 12-month
kind), SQS/SNS/EventBridge (well under any paid threshold at this volume),
DynamoDB provisioned 25/25 WCU/RCU (this stack uses a fraction of that
across 4 tables), the first 10 CloudWatch alarms and first 10 custom
metrics, 1 TB CloudFront egress, ACM public certificates, SSM Parameter
Store's standard tier, the first two AWS Budgets, 5 GB Application
Insights/Log Analytics ingestion per month, and (on a public repository)
unlimited GitHub Actions minutes. None of these are 12-month trial
allowances being counted as free by mistake - `docs/DESIGN.md` §9 is
explicit that only *always*-free lines are assumed free, specifically to
avoid the cost model quietly breaking a year in.

## If the budget alarm fires: what to destroy first

In order, cheapest-to-restore to most disruptive:

1. **`estate-demo.yml`'s schedule.** The Kubernetes estate's cost is
   already $0 (`kind` on a GitHub-hosted runner), but a schedule stuck in a
   retry loop or an unusually long-running dispatch still burns Actions
   minutes - free on this public repo, but the fastest thing to pause with
   zero blast radius on the rest of the system (disable the workflow, or
   remove the `schedule:` trigger in a follow-up PR) while investigating
   what's actually driving the alarm.
2. **Azure Functions.** Stop (not delete, to keep Terraform state and the
   Function apps' identities intact) `nordwind-triage-demo-notifications`
   and `nordwind-triage-demo-forwarder` in the Azure Portal, or `az
   functionapp stop`. This is the estate most likely to be the actual
   cause of an Azure-side alarm - Log Analytics ingestion is the one
   "classic Azure surprise" line in the whole model (`$2.30/GB` beyond the
   5 GB free tier), so check `daily_quota_gb` and recent ingestion volume
   before assuming it's a Functions execution-count problem.
3. **The bank Lambdas' EventBridge schedules.** `payments` and `auth` run
   on `rate(1 minute)` schedules that are the actual source of the AWS
   bank estate's background load; disabling those two EventBridge rules
   (`aws events disable-rule --name ...`, or the equivalent Terraform
   `aws_cloudwatch_event_rule` `is_enabled = false`) stops all further
   invocation-driven cost from that estate without touching the triage
   spine itself (ingest/worker/console API keep serving `bankops fire` and
   real Azure/Kubernetes alerts normally).

The triage spine itself (ingest, worker, DynamoDB, console) is never on
this list - it's the demo's actual subject, its Lambda/DynamoDB/SQS cost is
already $0 at this volume, and disabling it would silence real alerts, not
just synthetic ones.

## Reconciling against real billing

The table above is the *model*: every line traces to a resource definition
and a stated assumption (request counts, GB-s, always-free thresholds),
not a number read off an AWS or Azure bill - this repository's automation
has no network path to Cost Explorer or Cost Management (offline gates
only), so there is no live figure to substitute here without a human
pulling one. Close that gap once a month:

## One month later - checklist

- [ ] Pull the actual AWS Cost Explorer total (Billing -> Cost Explorer,
      filter to this account) and the Azure Cost Management total for the
      resource group; compare against the model above line by line - a
      line that's meaningfully off names exactly which assumption (request
      volume, alarm/metric count, storage growth) to revisit.
  - [ ] Look for a hidden overage from the "one thing on this list" alarm
      count/custom metric count creeping over the always-free 10 (fault
      chaos testing, a new milestone's alarms) - `docs/DESIGN.md` §9 flags
      this as the line most likely to drift.
- [ ] Check `known-issues-export`'s S3 bucket size - the 30-day lifecycle
      rule should keep it near-zero; a lifecycle rule silently disabled
      would show up as slow, compounding growth, not a spike.
- [ ] Check the ECR repository's image count (`aws ecr describe-images`) -
      the lifecycle policy keeps the last 10; confirm it's actually
      pruning, not just configured.
- [ ] Confirm `enable_dnssec` is still deliberately `false` (or, if turned
      on, that the ~$1/month KMS line has been added to the mental model
      above) - `infra/README.md`'s "DNSSEC" section has the current status.
- [ ] Compare Anthropic spend (Anthropic Console -> Usage) against the
      ≈$2.50/month model figure; a sustained mismatch usually means the
      daily alert cap (`var.daily_alert_cap`) or the chaos schedule
      changed without the cost model being revisited.
- [ ] Re-run `python scripts/check_links.py` after editing this file - the
      numbers above will need updating as new milestones land, and a stale
      table with a broken link in it is worse than an honest "not yet
      reconciled."
