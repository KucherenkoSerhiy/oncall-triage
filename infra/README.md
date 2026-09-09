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

## Chaos cookbook

Each command below fires a fault that drives one of the six alarms in
`alarms.tf` into `ALARM`, which publishes to the same SNS topic `ingest`
subscribes to - expect a verdict on the console within **~3-5 min** (the
EventBridge schedule / SQS delivery + the alarm's evaluation period + one
triage-worker invocation):

```bash
# payments 5xx burst -> nordwind-triage-demo-payments-Errors-Sev2
python -m cli.bankops chaos payments --mode errors --minutes 5

# ledger falls behind -> nordwind-triage-demo-ledger-ApproximateAgeOfOldestMessage-Sev2
python -m cli.bankops chaos ledger --mode lag --minutes 5

# auth JWKS rotation gone wrong -> nordwind-triage-demo-auth-AuthFailures-Sev2
python -m cli.bankops chaos auth --mode jwks-rotation --minutes 5
```

`python -m cli.bankops chaos --status` prints every active fault and the
minutes remaining; `python -m cli.bankops chaos <service> --clear` clears
one early. Faults also self-clear after `--minutes` (default 5) even if
never cleared explicitly, since `current_fault()` only returns a mode while
`until` is in the future.

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
