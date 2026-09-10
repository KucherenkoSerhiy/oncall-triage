# Infrastructure

Everything that has a cloud API is Terraform. Five root modules, two
audiences:

| Root | Applied by | State | Contains |
|---|---|---|---|
| `bootstrap/aws` | a human, once | local file, then never touched | Terraform state bucket, GitHub OIDC provider, the deploy role `deploy.yml` assumes |
| `bootstrap/azure` | a human, once | local file | resource group, app registration + federated credentials for GitHub, role assignment scoped to the resource group |
| `aws-ecr` | `deploy.yml` (`ecr` job, every run) | `s3://<bucket>/aws-ecr/terraform.tfstate` | the ECR repository for the triage-worker image |
| `aws` | `deploy.yml` (plan on PR, apply on merge) | `s3://<bucket>/aws/terraform.tfstate` (bucket in eu-north-1) | the triage brain, the AWS bank estate, DNS zone, budget, dashboard |
| `azure` | `deploy.yml` | `s3://<bucket>/azure/terraform.tfstate` | the Azure bank estate, alert forwarder, Azure Monitor rules, budget |

The bootstrap modules are the only place a human credential is ever used;
their outputs become GitHub repository *variables* (not secrets - none of
them is secret): `AWS_DEPLOY_ROLE_ARN`, `TF_STATE_BUCKET`, `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. The one real secret,
`BUDGET_EMAIL`, is an environment secret only because it is personal data.

**The Kubernetes estate is deliberately not here.** `cards-authorization`,
`fraud-scoring` and `open-banking-api` run in [kind](https://kind.sigs.k8s.io/),
not on a Terraform-provisioned cloud cluster - ADR
[0007](../docs/adr/0007-kubernetes-on-kind.md) (design decision D7): a
managed cluster's node VM is the one thing that isn't free. There is no
`infra/kubernetes` root; the chart is `deploy/helm/nordwind-bank`, the
cluster config is `deploy/kind/cluster.yaml`, and `task estate-up/down`
(`.github/workflows/estate-demo.yml` in CI) stand in for `terraform
plan`/`apply`. See `docs/runbooks/kubernetes-estate.md`.

## Bootstrap (once)

```bash
# AWS - needs an identity that can create IAM roles and S3 buckets
cd infra/bootstrap/aws
terraform init && terraform apply
terraform output            # -> deploy_role_arn, state_bucket

# Azure - needs `az login` with rights to create app registrations
cd ../azure
terraform init && terraform apply
terraform output            # -> client_id, tenant_id, subscription_id
```

Then set the five repository variables in GitHub, create the `demo`
environment with yourself as required reviewer, and every later change
flows through pull requests.

## What `infra/aws-ecr` deploys

Just the ECR repository for the triage-worker image (`ecr.tf`): immutable
tags, scan on push, AES256 encryption, a lifecycle policy keeping the last
10 images. It is its own root, applied before `infra/aws`, purely to avoid
a chicken-and-egg race on a fresh account - see "Deploy ordering" below.

## What `infra/aws` deploys

The alert spine (M2), the real triage worker (M3), and the AWS bank estate
(M4, see below): everything needed to ingest an alert, queue it, triage it
with Claude, and let an operator read the result.

- **DynamoDB** (`storage.tf`): `alerts`, `verdicts`, `known-issues` -
  provisioned 5/5 capacity (2/2 on GSIs) to stay in the always-free tier.
- **SQS + SNS** (`messaging.tf`): the `alerts` queue (with a DLQ after 3
  failed attempts) and the `alarms` SNS topic that will carry M4's alarm
  producers into ingest.
- **Lambda** (`lambdas.tf`): `ingest` and `console-api` are Python 3.12 on
  arm64, packaged from one shared code zip. `triage-worker` is an
  **image-based** Lambda (arm64, 1024 MB, 120 s timeout) - its image comes
  from the `infra/aws-ecr` repository, referenced with
  `data "aws_ecr_repository"` and tagged by `var.worker_image_sha`. Every
  role is scoped to exactly the tables/queue/parameters each function
  touches; `triage-worker`'s role additionally has `dynamodb:Query` on the
  alerts table's `by_status` index and `dynamodb:Query`/`PutItem` on
  known-issues (what the agent's tools need).
- **API Gateway** (`api.tf`): an HTTP API at `api.<domain>` routing to
  `ingest` (`POST /alerts`) and `console-api` (everything else), with
  access logging and throttling.
- **Console** (`console.tf`): a private S3 bucket behind CloudFront (Origin
  Access Control) serving `console/` at the zone apex.
- **Secrets** (`secrets.tf`): two SSM `SecureString` parameters, generated
  in Terraform so no plaintext ever lands in the repo. The Anthropic key
  (`lambdas.tf`) is a third SSM parameter, deliberately **not** created by
  Terraform - see "Anthropic API key" below.

An operator using `bankops` against a deployed environment reads the two
generated secrets from SSM:

```bash
aws ssm get-parameter --with-decryption --name /nordwind-triage/demo/ingest-hmac-secret --query Parameter.Value --output text
aws ssm get-parameter --with-decryption --name /nordwind-triage/demo/console-token --query Parameter.Value --output text
```

## What the AWS bank estate deploys

Three tiny Lambdas that pretend to be a bank, plus the fault control plane
`bankops chaos` and the console API's `/chaos` routes flip on and off
(`bank.tf`), and the six CloudWatch alarms that turn a fault into a verdict
(`alarms.tf`):

- **`payments`** (EventBridge `rate(1 minute)`): processes a batch of 5
  synthetic authorisations and hands each one to `ledger` over the
  **ledger queue** (SQS + DLQ, `maxReceiveCount` 5). Faults: `errors` (raise,
  drives the Lambda `Errors` metric), `latency` (sleep 2.5s, drives
  `Duration`), `pool` (emit `PoolExhausted` then raise).
- **`ledger`** (SQS event source, batch 5, `ReportBatchItemFailures`):
  "posts" each authorisation. Faults: `lag` (fail every record so the queue
  backs up and `ApproximateAgeOfOldestMessage` grows), `reconciliation-mismatch`
  (emit a metric, still process normally).
- **`auth`** (EventBridge `rate(1 minute)`): "issues" 20 tokens. Faults:
  `jwks-rotation` (emit `AuthFailures`, then raise), `lockouts` (emit
  `AccountLockouts`, still succeed).
- **`bank-faults`** DynamoDB table (provisioned 1/1): one item per service,
  `{service, mode, until, set_at, set_by}`, read by `bank/aws/common.py`'s
  `current_fault()` and written by the console API's `/chaos` routes.

Every Lambda is Python 3.12 on arm64 (128 MB, 10 s timeout), packaged from a
zip scoped to `bank/` only (`data.archive_file.bank` in `bank.tf`, separate
from the `services` zip in `lambdas.tf`), with its own role scoped to
exactly what it touches: read-only on the faults table, `payments` can send
to the ledger queue, `ledger` can consume it, and all three can
`cloudwatch:PutMetricData` under a `cloudwatch:namespace = Nordwind/Bank`
condition (that action accepts no resource ARN).

## Self-observability (M9a)

`observability.tf` gives an operator one place to look before reaching for
`diagnose.yml`: a CloudWatch dashboard (`aws_cloudwatch_dashboard`, named
after `local.name_prefix`) with ingest/worker/API Gateway/queue metrics,
the bank estate's four `Nordwind/Bank` metrics, and the SLO widgets below;
and five alarms into a **human-only** `ops` SNS topic (e-mail subscription
to `var.notification_email`) — deliberately *not* the `alarms` topic
(`messaging.tf`), since alarms about the triage brain itself feeding back
into ingest would have the brain triage itself:

| Alarm | Fires when |
|---|---|
| `ops-IngestErrorRatio` | ingest's `Errors / Invocations` > 5% over 5 min (metric math, guarded against a 0-invocation divide) |
| `ops-WorkerErrors` | the triage worker's `Errors` >= 3 over 15 min |
| `ops-AlertsDlqDepth` | the alerts DLQ has >= 1 message |
| `ops-WorkerDurationP95` | the triage worker's p95 `Duration` > 60s over 5 min |
| `ops-CapReached` | `Nordwind/Triage`'s `CapReached` custom metric >= 1 over 5 min — `var.daily_alert_cap` is short-circuiting verdicts |

`CapReached` is emitted by `services/triage_worker/metrics.py` on the cap
short-circuit path only (`handler.py`); the worker's IAM role gained
`cloudwatch:PutMetricData` scoped to the `Nordwind/Triage` namespace, same
condition-based pattern as the bank Lambdas' `Nordwind/Bank` metrics.

A daily Lambda, `slo-reporter` (`bank.ops.slo_reporter.handler`, own IAM
role, 128 MB, 60s, EventBridge `cron(15 0 * * ? *)`), reads yesterday's
triaged alerts and verdicts and publishes `VerdictLatencyP95`,
`AlertsTriaged` and `SloAttainment` — the SLO itself, what counts, and the
error budget are in [`docs/slo.md`](../docs/slo.md).

**Cost**: the dashboard is free (first one). Five ops alarms plus
`alarms.tf`'s six bank alarms put the account at 11 CloudWatch alarms — one
over the always-free 10, at ~$0.10/month; every custom metric (4
`Nordwind/Bank` + 4 `Nordwind/Triage` = 8) still fits the free 10. See
`docs/DESIGN.md` section 9 ("Cost model").

## What `infra/azure` deploys

The Azure half of the bank estate (M5): one Function app pretending to be
customer-notifications, Azure Monitor rules that turn its faults into
alerts, and the always-on alert forwarder those rules (and, from M6, an
Alertmanager route B) call into.

- **Storage** (`storage.tf`): one `Standard`/`LRS` storage account
  (`nordwindtriage<random 6>`, TLS 1.2 minimum, no public blob access),
  shared by both Function apps' control-plane data (triggers, locks,
  `WEBSITE_RUN_FROM_PACKAGE`). Y1 (Consumption) Function apps authenticate
  to it with an account key - there is no managed-identity path for that
  connection on this plan, so `shared_access_key_enabled` stays `true`
  (documented again as a checkov skip in `.checkov.yaml`).
- **Observability** (`functions.tf`): a Log Analytics workspace
  (`PerGB2018`, 30-day retention, `daily_quota_gb = 0.2` so verbose logging
  can't run away with the bill) and a workspace-based Application Insights
  component with `sampling_percentage = 20`.
- **Compute** (`functions.tf`): one Linux Consumption (`Y1`) service plan
  and two `azurerm_linux_function_app`s (Python 3.12, system-assigned
  identity, `https_only`), `nordwind-triage-demo-notifications` and
  `nordwind-triage-demo-forwarder`. Each deploys standalone from a
  `zip_deploy_file` built by `data.archive_file.functions` from its own
  `bank/azure/<app>/` directory plus `bank/azure/_shared/` copied in as a
  sibling folder at the zip root (see `bank/azure/README.md`'s
  "sibling-import trick"); `ENABLE_ORYX_BUILD = "true"` and
  `SCM_DO_BUILD_DURING_DEPLOYMENT = "true"` make Oryx install each app's
  `requirements.txt` on deploy. **The first deploy takes ~3 minutes to
  warm** (Oryx build + cold start) before the timer trigger starts firing.
- **Alerting** (`alerts.tf`): an action group (`nordwind-triage-demo-alerts`,
  short name `nwtriage`) with a webhook receiver pointing at the
  forwarder's function URL - including its default function key, read back
  with `data.azurerm_function_app_host_keys` since the forwarder's HTTP
  trigger is function-key authed and the action group has no other way to
  authenticate. Three rules fire into it: a metric alert on
  `exceptions/count` from the Application Insights component (timer
  failures surface as exceptions - `Http5xx` on the site would miss a
  timer trigger entirely), and two log alerts (`scheduled_query_rules_alert_v2`,
  KQL over the Log Analytics workspace) on the `provider_429` and
  `notifications_backlog` custom metrics.

### Why app settings are plaintext (v1)

Same trade-off as the AWS Lambdas' environment variables: `CONSOLE_TOKEN`
and `INGEST_HMAC_SECRET` land in each Function app's configuration as
ordinary (non-Key-Vault-backed) app settings, visible in plaintext to
anyone with Contributor access on the resource group. `infra/azure` never
talks to AWS itself (M1), so it can't read the two SSM parameters that hold
the real values back on its own - `deploy.yml`'s `plan`/`apply` steps read
them with the AWS role (same commands as the `smoke` job) and pass them in
as `-var="console_token=..." -var="ingest_hmac_secret=..."`, masked with
`::add-mask::` before they ever reach a log line. Key Vault references are
the M9 hardening upgrade.

## Chaos cookbook

Each command below fires a fault that drives one of the six AWS alarms in
`alarms.tf` into `ALARM` (published to the same SNS topic `ingest`
subscribes to) or one of the three Azure Monitor rules in `alerts.tf` -
expect a verdict on the console within **~3-5 min** on AWS (EventBridge
schedule / SQS delivery + the alarm's evaluation period + one
triage-worker invocation) or **~5-7 min** on Azure (Azure Monitor evaluates
every minute over a 5-minute window, one step slower than CloudWatch):

```bash
# payments 5xx burst -> nordwind-triage-demo-payments-Errors-Sev2
python -m cli.bankops chaos payments --mode errors --minutes 5

# ledger falls behind -> nordwind-triage-demo-ledger-ApproximateAgeOfOldestMessage-Sev2
python -m cli.bankops chaos ledger --mode lag --minutes 5

# auth JWKS rotation gone wrong -> nordwind-triage-demo-auth-AuthFailures-Sev2
python -m cli.bankops chaos auth --mode jwks-rotation --minutes 5

# SMS/e-mail provider 429s -> nordwind-triage-demo-customer-notifications-Provider429-Sev2
python -m cli.bankops chaos customer-notifications --mode provider-429 --minutes 5

# notifications backlog grows -> nordwind-triage-demo-customer-notifications-Backlog-Sev3
python -m cli.bankops chaos customer-notifications --mode backlog --minutes 5
```

`python -m cli.bankops chaos --status` prints every active fault and the
minutes remaining; `python -m cli.bankops chaos <service> --clear` clears
one early. Faults also self-clear after `--minutes` (default 5) even if
never cleared explicitly, since `current_fault()` only returns a mode while
`until` is in the future.

### Proving it without a laptop

`scripts/chaos_probe.py` runs the same experiment unattended: set a fault,
wait for the estate's own alarm to arrive at the spine, wait for the
verdict, clear the fault, fail if the verdict came from a stub or (with
`--expect-known`) did not match the taught known issue. `--timeout`
overrides the default 10-minute wait - the deploy workflow's
`notifications-429` option raises it to 12 minutes for Azure Monitor's
slower evaluation. The deploy workflow exposes it as the `chaos_probe`
dispatch input:

```bash
gh workflow run deploy.yml -f root=aws -f chaos_probe=payments-pool
gh workflow run deploy.yml -f root=azure -f chaos_probe=notifications-429
```

The smoke job then prints `OK: alert_id=... alert=...-payments-PoolExhausted-Sev3 source=cloudwatch known=True action=ack model=...`.
Every milestone's live probe from M4 on is recorded this way.

## Anthropic API key

The triage worker reads its Claude API key from
`/nordwind-triage/demo/anthropic-api-key`, a `SecureString` SSM parameter
that Terraform only *reads* (`data "aws_ssm_parameter"` in `lambdas.tf`) -
it is a human secret, not something Terraform should generate or own. If
it doesn't exist, `terraform plan`/`apply` fails with a clear message from
a `precondition` on `aws_lambda_function.triage_worker` naming the command
below.

Set it once, or rotate it, with the AWS CLI (needs an identity with
`ssm:PutParameter` on the project's parameters - the deploy role has it):

```bash
aws ssm put-parameter \
  --name /nordwind-triage/demo/anthropic-api-key \
  --type SecureString \
  --value <key> \
  --overwrite
```

Or, without a local AWS credential: store the key as the repository secret
`ANTHROPIC_API_KEY` (`gh secret set ANTHROPIC_API_KEY`). Every non-PR run of
`deploy.yml` syncs that secret into the SSM parameter with the deploy role
(masked in the log) before `plan`; a `workflow_dispatch` `anthropic_api_key`
input overrides it for one run. Rotation is therefore `gh secret set` plus
any deploy.

## Deploy ordering

`deploy.yml` runs `ecr` -> `image` -> `plan` -> `apply` (`smoke` last, on
`apply` success). `ecr` applies `infra/aws-ecr` directly (no plan/approval
step - it only ever touches the registry) so the repository exists before
`image` builds and pushes `services/triage_worker/Dockerfile` for
`linux/arm64` and tags it `<repo>:sha-<git sha>` + `<repo>:latest`. Only
then does `infra/aws`'s `plan`/`apply` run, with
`-var="worker_image_sha=sha-<git sha>"` so the Lambda's `image_uri` points
at an image that already exists. `ecr` and `image` are skipped on pull
requests (they only run on pushes to the default branch and on
`workflow_dispatch`); a PR still plans successfully because
`var.worker_image_sha` defaults to `latest`.

## Diagnosing the live spine

`.github/workflows/diagnose.yml` (Actions -> diagnose -> Run workflow) is a
read-only look at AWS with the deploy role: Lambda errors / throttles /
p95 per function, queue depths including the DLQs, account concurrency,
the worker's configuration (secrets redacted), the daily LLM cap counter,
the newest worker and ingest log lines, and one alert record by id. Use it
first when a smoke probe reports `no verdict within 90s` or a chaos probe
never sees its alert.

## Rollback

`worker_image_sha` accepts any tag already in the ECR repository (images
are immutable and named by git SHA, so nothing is ever overwritten).
Redeploy an earlier build with:

```bash
gh workflow run deploy.yml -f root=aws -f worker_image_sha=sha-<sha>
```

`image` still runs (it always does on `workflow_dispatch`) and pushes the
current commit as a new image, but the explicit `worker_image_sha` input
wins over the freshly-built one, so the Lambda points at the older,
already-verified image.

### Image format

The `image` job builds with `provenance: false` / `sbom: false`. Lambda
accepts only a single-platform image manifest; buildx's default provenance
attestation wraps the push in an OCI image index and `CreateFunction`
fails with "image manifest, config or layer media type ... is not
supported". If a tag was pushed without those flags, it cannot be fixed in
place (tags are immutable) - push the next commit instead.

## One-time account prerequisites (outside Terraform)

Some AWS services create a *service-linked role* the first time they are
used in an account. Creating one needs `iam:CreateServiceLinkedRole`, which
the deploy role deliberately does not hold, so these are created once by a
human session (CloudShell in the console is enough - no key involved):

```bash
# API Gateway custom domain names (used by infra/aws api.tf)
aws iam create-service-linked-role --aws-service-name ops.apigateway.amazonaws.com
```

Symptom when missing: `apply - aws` fails on `aws_apigatewayv2_domain_name`
with "Caller does not have permissions to create a Service Linked Role".
Re-running the deploy after the command succeeds continues from the saved
state.

## Conventions

- Provider default tags on every resource: `project`, `env`, `owner`,
  `cost_center`, `managed_by`; components additionally carry
  `c4_container` matching an identifier in `docs/c4/workspace.dsl` (the
  drift check keys on it).
- Names: `nordwind-triage-<env>-<component>`.
- `terraform fmt`, `validate`, `tflint` and `checkov` run in CI for all five
  roots; policy exceptions live in `.checkov.yaml` with a reason each.
- The image is pushed by `deploy.yml`'s `image` job using the OIDC deploy
  role (its existing `ecr:*` grant already covers push) - no separate
  credential or role change needed.

## Decisions taken while shipping the AWS bank estate (M4)

Notes on places where `docs/specs/m4-aws-bank-estate.md` left a choice open.

### The `bank-faults` table name gets the project prefix

Requirement 1 names the table `bank-faults`, but every other resource in
this stack follows `nordwind-triage-<env>-<component>` (`infra/README.md`
"Conventions"). The Terraform resource is named
`${local.name_prefix}-bank-faults`; the literal name only matters to
`BANK_FAULTS_TABLE`, which every reader (`bank/aws/common.py`,
`services/console_api/store.py`) gets from an environment variable, not a
hardcoded string, so the prefix is invisible to application code.

### The bank zip is built the same way as the services zip

Requirement 6 says the Lambda zip is "built from `bank/aws/`". Taken
literally that would flatten `bank/aws/payments/handler.py` to
`payments/handler.py` inside the archive, breaking the `bank.aws.payments`
import path every handler and `bank/aws/common.py` itself relies on.
Instead `data.archive_file.bank` (`bank.tf`) mirrors
`data.archive_file.services` (`lambdas.tf`): built from the repo root with
everything except `bank/` excluded, so the zip's top-level package is
`bank`, matching the handler dotted paths
(`bank.aws.payments.handler.lambda_handler` etc.) unchanged.

### Chaos route status codes

The spec doesn't name status codes beyond `201`/`204` for success. An
unknown `{service}` (not `payments`/`ledger`/`auth`) is `404` on both
`POST` and `DELETE /chaos/{service}` - there's no such resource to act on.
An unknown `mode` for a valid service is `400` - the resource exists, the
request body is invalid. `DELETE` is idempotent: clearing a fault that was
never set is still `204`, unlike `known-issues`' `404`-on-missing, because
"no fault" is deliberately not the same case as "not a valid service".

### One source of truth for valid chaos modes

`VALID_MODES` (service -> its modes) lives in `bank/aws/common.py` and is
imported by both `services/console_api/handler.py` (server-side validation,
requirement 1) and `cli/bankops/commands.py` (client-side validation,
requirement 8), rather than duplicating the three-service mapping in three
places.

### `AlarmDescription` uses `;` after `service=<name>`, not `:`

`services/ingest/adapters/cloudwatch.py`'s `service=([^\s,;]+)` regex stops
at whitespace, comma or semicolon - not a colon. `alarms.tf`'s descriptions
read `"service=payments; <sentence>"` so the captured service is exactly
`payments`, not `payments:`.

## Decisions taken while shipping the worker image (M3b)

Notes on places where `docs/specs/m3b-worker-image-pipeline.md` left a
choice open, or where two of its requirements pulled in different
directions, and how this implementation resolved them.

### ECR repository location (req 1 vs req 6)

Requirement 1 names the file `infra/aws/ecr.tf`. Requirement 6 then walks
through *why* that placement is wrong (a fresh-account apply would need
the image to exist before the repository that would hold it does) and
concludes the repository "moves to its own tiny root `infra/aws-ecr`".
Requirement 6 is the more specific, later-reasoned instruction, so the
`aws_ecr_repository` resource (with everything requirement 1 asks of it -
`IMMUTABLE` tags, scan on push, AES256, a 10-image lifecycle policy, the
`worker` C4 tag, and a `worker_repository_url` output) lives in
`infra/aws-ecr/ecr.tf`. `infra/aws` reads it back with
`data "aws_ecr_repository"` in `data.tf`.

### `:latest` under an IMMUTABLE repository

An ECR repository with `image_tag_mutability = IMMUTABLE` rejects *any*
tag being pushed a second time, including `:latest` - so the second-ever
deploy would fail to push `:latest` even though nothing asks it to
overwrite content addressed by a SHA. The `image` job works around this
by deleting the existing `:latest` tag (`aws ecr batch-delete-image`,
ignoring "not found" on the very first push) immediately before pushing:
`sha-<sha>` tags stay genuinely immutable (never deleted, never
reused), while `:latest` behaves like the mutable rolling alias it is
meant to be.

### `dynamodb:GetItem` on the verdicts table

The spec's IAM list for the triage-worker role is "`dynamodb:Query` on
alerts + `by_status`, `dynamodb:Query`/`PutItem` on known-issues, plus
`dynamodb:UpdateItem` on verdicts (the daily-cap counter)". It doesn't
mention `GetItem` on verdicts, but `handler.py`'s redelivery
short-circuit (`verdicts_table.get_item(...)`, predating this milestone)
needs it - without it every invocation would fail with AccessDenied. Added
it to the `VerdictsTable` statement alongside `PutItem`/`UpdateItem`,
since shipping a worker that cannot run isn't a smaller/safer
implementation of the spec.

### The "seeded known issue" for the second smoke probe (req 8)

Nothing else in the spec asks Terraform to load `known_issues.json`
into the known-issues DynamoDB table, and a fresh environment's table
starts empty. Rather than add a new Terraform resource (and the
`dynamodb:PutItem`-from-Terraform permission that would need) just to
pre-populate one row for a smoke test, `scripts/smoke.py` teaches the
issue itself: it `POST /known-issues`s the `payments` /
"connection pool exhausted" pattern (using the console bearer token it
already holds) immediately before firing the alert that should match it.
This keeps the probe self-contained and uses only what the console API
already exposes.

### `LOG_LEVEL`

The spec lists `LOG_LEVEL` among the Lambda's environment variables
without naming a source. `handler.py` already does
`os.environ.get("LOG_LEVEL", "INFO")`, so the Lambda environment sets it
to the literal `"INFO"` - no new Terraform variable, since nothing calls
for one.

### `ecr` / `image` jobs are not gated by the `demo` environment

Only `apply` in the existing pipeline requires the `demo` environment's
human approval. `ecr` and `image` run before `plan` is even posted for
review and only on pushes to the default branch or `workflow_dispatch`
(never on a pull request), matching the spec's literal ordering
(`ecr` -> `image` -> `plan` -> `apply`). Gating them on `demo` too would
mean two separate approval prompts per run for no additional safety (the
registry and the image are inert until a Lambda points at them, which
`apply` still gates).

## Decisions taken while shipping the Azure Functions estate (M5b)

Notes on places where `docs/specs/m5b-azure-terraform.md` left a choice
open.

### `c4_container` tags on shared Functions plumbing

The spec's tag enum for this root is exactly three values -
`notifications` / `forwarder` / `monitor` - but four of the new resources
(the storage account, the service plan, the Log Analytics workspace, the
Application Insights component) back *both* Function apps and don't map
to a single container the way a Lambda maps to its log group on the AWS
side. All four get `monitor`: Log Analytics and Application Insights
literally feed the alert rules (already named `monitor` in
`docs/c4/workspace.dsl`), and the storage account / service plan are
generic hosting plumbing with no more claim to `notifications` than to
`forwarder`. The two Function apps themselves get their own specific tag.

### Metric namespace for the `exceptions/count` alert

`azurerm_monitor_metric_alert.criteria.metric_namespace` is a required
field the spec doesn't name. Application Insights components publish
their metrics (including `exceptions/count`) under the namespace
`microsoft.insights/components` - the value every Azure Monitor example
for this metric uses; there's no alternative namespace to choose from for
this metric on this resource type.

### `archive_file` merging two source directories

`archive_file` has no attribute for zipping two separate directories into
one archive with one nested as a subfolder (unlike a single `source_dir`,
which zips one directory as-is). Each app's zip is instead built from a
map of `zip path -> local file path` assembled with `fileset()` over the
app's own directory and `bank/azure/_shared/` (filtered to drop
`__pycache__`/`.pyc`), fed to a `dynamic "source"` block - functionally
identical to "package `bank/azure/<app>/` plus `bank/azure/_shared/` at
the zip root" (requirement 1), just built by hand since Terraform has no
built-in "merge two directories" primitive.

### Where the SSM read for `infra/azure` lives in `deploy.yml`

Requirement 3 says the `plan`/`apply` steps "first read the two SSM
parameters ... and pass" them as `-var` flags - read literally, that's a
step *before* `terraform plan`/`apply`. Doing it as a separate step would
mean carrying the two secret values through `GITHUB_OUTPUT` into the next
step, which GitHub's own docs warn against (an output's value is not
masked at rest, only in log lines after `::add-mask::` - a real risk on
this public repo). Instead the read happens at the *top* of the same
`terraform plan` / `terraform apply` step, in the same shell process, so
the secrets never leave a masked, single-step scope; "first" is satisfied
in execution order, not job-step order.
