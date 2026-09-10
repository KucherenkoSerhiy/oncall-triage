# Runbook: secrets rotation

Five secrets, five different rotation mechanisms - this runbook is one
section per secret: owner, where it lives, what reads it, the rotation
steps, and what breaks in the gap between "rotated at the source" and
"every reader caught up." See [ADR 0017](../adr/0017-runbooks-derived-from-incidents.md)
for why this runbook cites issues the way it does.

## Console token

- **Owner**: the repository owner (this is the console's own bearer token,
  not a cloud credential).
- **Where it lives**: `random_password.console_token`
  (`infra/aws/secrets.tf`) -> SSM `SecureString`
  `/nordwind-triage/demo/console-token`.
- **What reads it**: `console-api`'s `CONSOLE_TOKEN` env var (from the SSM
  value, at `infra/aws` deploy time); every browser's `localStorage`
  (`triage.token`, entered once via the console's token dialog); any local
  `bankops` invocation (`SMOKE_TOKEN`/config); the Azure
  `customer-notifications` Function's `CONSOLE_TOKEN` app setting (reads
  the fault status via the console API's `/chaos` route -
  `bank/azure/customer_notifications/notifications.py`); `scripts/chaos_probe.py`
  and `scripts/smoke.py`, both of which read `SMOKE_TOKEN` fresh from the
  environment on every run rather than caching it, so they never go stale
  mid-drill the way a browser tab does.

**Rotation steps**: bump `random_password.console_token`'s `keepers` value
in `infra/aws/secrets.tf` (any change forces `random_password` to
regenerate) and merge/deploy as normal. The next `infra/aws` apply
recreates the password, updates the SSM parameter, and updates
`console-api`'s own `CONSOLE_TOKEN` env var **in the same apply** - the
verifier and the SSM value change atomically. The Azure app setting only
picks it up on `infra/azure`'s **next** apply (its plan/apply steps read
the AWS SSM value fresh via `-var=console_token=...`), which is why
requirement 3's ordering note matters in practice: a deploy that touches
both roots rotates both in one run; a rotation that only re-applies
`infra/aws` (a `workflow_dispatch -f root=aws`) leaves the Azure setting
stale until the next full deploy.

**What breaks in between**: every holder of the old token - browsers,
local `bankops` configs, the notifications Function until its own redeploy
- gets HTTP 401 from the console API. See
[`docs/runbooks/triage-spine.md`](triage-spine.md#console-401s-token-rotation)
for the operator-facing symptom and fix (fetch the new value from SSM,
click **Change token** in the console, update any local config).

**Worked example - "[chore: rotate the console bearer token (value was
visible in a screenshot during
setup)](https://github.com/KucherenkoSerhiy/oncall-triage/issues/31)"
(#31)**: a screenshot captured for documentation/setup purposes showed the
console with the bearer token visible, exposing it outside the
repository's normal secret boundary. The token grants read/write on
alerts, verdicts and known-issues - not cloud access - so the response is
a straightforward rotation rather than a wider credential audit: bump the
`keepers` value, deploy, update every reader. #31 names this exact runbook
as the blocker on doing that ("blocked until M9e's secrets-rotation
runbook exists, or do it ad hoc and record the steps here") - this section
is that runbook; the rotation itself is recorded below.

**Rotation status: prepared, not yet executed - a real open item, not a
placeholder.** This slice ships the code-level half of the fix (the
`keepers` bump on `random_password.console_token` in
`infra/aws/secrets.tf` above), which is everything a pull request *can*
ship - the actual rotation only happens on the next `infra/aws` apply, and
applying Terraform needs the deploy role's cloud credentials, which this
documentation pass does not have (the same human-in-the-loop boundary
`docs/DESIGN.md` §6.2 draws around every apply in this repository: PRs
produce the change, a human/CI apply executes it). **Closing out #31 needs
a human to**:

1. Merge this PR (or otherwise land the `keepers` bump on `master`).
2. Run (or wait for the push-triggered) `deploy.yml` against `infra/aws` -
   `gh workflow run deploy.yml -f root=aws`, or `-f root=all` to rotate
   both this and pick up the Azure app setting in the same pass.
3. Record the run id, start/finish timestamps and the smoke probe's output
   line here, in the same table format as
   [`docs/runbooks/deploy-and-rollback.md`](deploy-and-rollback.md#the-rollback-drill)'s
   rollback drill, and close #31 referencing it.

| Step | Run | Started | Finished | Result | Smoke |
|---|---|---|---|---|---|
| Rotate console token (`infra/aws` apply, keeper `m9e-2026-09-10`, PR #89) | [34476339421](https://github.com/KucherenkoSerhiy/oncall-triage/actions/runs/34476339421) | 2026-09-10 12:22:16Z | 12:34:12Z | success (both approval legs) | `OK: alert_id=01M25MYPE9E2GG108RQ7BZQQ1K action=ack; known_alert_id=01M25MZ1Z8RPFWG29CBHRFC5TA` - the smoke read the new token from SSM |

The Azure `notifications` app setting was re-synced by a follow-up `deploy.yml -f root=azure` dispatch straight after (the two apply legs run in parallel, so the Azure leg of the rotating run can read the previous token). The row above is the record; a future rotation repeats the keeper bump and refills it. Historically: until that row was filled in, the rotation counted as **not done** - the
Terraform change is real and correct, but nobody has run it yet, and this
runbook says so plainly rather than implying otherwise.

## Ingest HMAC secret

- **Owner**: the repository owner.
- **Where it lives**: `random_password.ingest_hmac_secret`
  (`infra/aws/secrets.tf`) -> SSM `SecureString`
  `/nordwind-triage/demo/ingest-hmac-secret`.
- **What reads it**: `ingest`'s `INGEST_HMAC_SECRET` env var (the
  **verifier** - every inbound webhook is checked against this value);
  `scripts/smoke.py` and `scripts/chaos_probe.py` (read fresh from SSM
  each run, via the `smoke`/`plan`/`apply` jobs' own `aws ssm
  get-parameter` steps - never stale); the Azure `alert_forwarder`
  Function's `INGEST_HMAC_SECRET` app setting (same `-var` flag pattern as
  the console token, `infra/azure` apply time); the Kubernetes
  `nordwind-ingest` Secret that `kafka-relay`'s Deployment mounts (created
  by `task estate-up` / `estate-demo.yml` from a **fresh SSM read at that
  moment**, not managed by Terraform - see
  [`docs/runbooks/kubernetes-estate.md`](kubernetes-estate.md#the-nordwind-ingest-secret)).
  Four producers (bankops, forwarder, kafka-relay's relayed alerts, and any
  future adapter), one verifier.

**Rotation steps**: same `keepers` mechanism as the console token, on
`random_password.ingest_hmac_secret`. `infra/aws`'s apply rotates the SSM
value and `ingest`'s own env var atomically, exactly like the console
token.

**What breaks in between, and the choice to make**: the moment `infra/aws`
applies, `ingest` verifies against the **new** secret - but the Azure
forwarder (until its own `infra/azure` apply) and `kafka-relay` (until the
next `task estate-up`/`estate-demo.yml`) are still **signing** with the
**old** one. Every webhook from those two producers gets HTTP 401 during
that gap. Two ways to handle it:

1. **Accept a short window.** Deploy `infra/aws` and `infra/azure` together
   (the normal path - one push, `plan` for both roots, `apply` for both in
   the same run), and let the Kubernetes estate catch up whenever it next
   runs `task estate-up`. Nothing is silently lost: Alertmanager/the relay
   don't retry indefinitely, but a periodic fault (the chaos scenarios all
   fire repeatedly over minutes) produces another attempt after the relay's
   next reconcile, and a 401'd webhook is visible in `kafka-relay`'s log
   (`relay_dropped_total`) rather than disappearing without a trace. This
   is the lower-effort default and what a routine deploy-triggered rotation
   does automatically.
2. **Rotate producers first.** Manually push the new secret to `kafka-relay`
   (re-run the `kubectl create secret ... | kubectl apply -f -` command in
   `docs/runbooks/kubernetes-estate.md`) and confirm the Azure app setting
   before merging the `infra/aws` change that flips the verifier, so no
   webhook is ever signed with a secret `ingest` doesn't yet recognise.
   Zero-401 rotation, at the cost of a manual step outside the normal
   pipeline and a window where the *old* secret verifies while producers
   already hold the *new* one (the same trade, inverted, and just as short).

Either way the window is minutes, not hours, and this repo defaults to (1)
- accept it - because nothing pages on a 401'd synthetic/demo webhook and
the DLQ/retry story elsewhere in this runbook set already assumes
transient delivery failures are normal, not incidents.

**Verify**: `python scripts/smoke.py` (verifies the AWS-side signature
immediately); `bankops chaos customer-notifications --mode provider-429`
or a Kubernetes chaos scenario once each producer has caught up.

## Anthropic API key

- **Owner**: the repository owner (the account the key belongs to).
- **Where it lives**: the `ANTHROPIC_API_KEY` **repository secret** -
  deliberately **not** a Terraform-managed `random_password`, since
  Terraform can generate a password but not an Anthropic API key.
- **What reads it**: the `triage-worker` Lambda's own `ANTHROPIC_API_KEY`
  env var, sourced from SSM parameter
  `/nordwind-triage/demo/anthropic-api-key` - a parameter Terraform only
  *reads* (`data "aws_ssm_parameter"` in `lambdas.tf`), never creates.

**Rotation steps**: `gh secret set ANTHROPIC_API_KEY` with the new key,
then any deploy (push, or `gh workflow run deploy.yml`). Every non-PR run
of `deploy.yml`'s `anthropic_key` job syncs the repository secret (or a
one-off `workflow_dispatch anthropic_api_key` input, which wins if given)
into the SSM parameter, masked before it can reach a log line. `infra/aws`'s
subsequent `plan`/`apply` then picks up the new SSM value into the worker's
env var the same way it always does.

**What breaks in between**: nothing until the *old* key is revoked at
Anthropic - the worker keeps working against whichever key SSM last held.
Revoke the old key only after confirming a chaos probe or smoke run
succeeded against the new one.

**Verify**: `scripts/smoke.py` / `scripts/chaos_probe.py` both assert the
verdict's `model` is a real model id, not `"stub"` - a bad or revoked key
makes the worker fall back to the stub path, which both probes treat as a
hard failure.

## Cloudflare API token

- **Owner**: the repository owner (scoped to `Zone:Read` + `DNS:Edit` on
  `serhiykucherenko.dev` only, per `docs/DESIGN.md` §14).
- **Where it lives**: the `CLOUDFLARE_API_TOKEN` repository secret.
- **What reads it**: only the `cloudflare` Terraform provider inside
  `infra/aws` (`dns_delegation.tf`'s NS delegation records, and
  `dnssec.tf`'s DS record) - every other resource in `infra/aws` is
  untouched by this token, even though it's exported as a job-level env
  var for the whole `plan`/`apply` steps.

**Rotation steps**: generate a new token in the Cloudflare dashboard scoped
identically to the old one, `gh secret set CLOUDFLARE_API_TOKEN`, then any
`infra/aws` plan/apply. There is nothing to keep in sync across multiple
readers - one secret, one consumer.

**What breaks in between**: nothing live - the delegation NS records and
the DNSSEC DS record are already published; a stale/revoked token only
blocks the **next** `infra/aws` plan/apply from succeeding (Cloudflare API
calls fail), it does not affect DNS resolution for existing records.

**Verify**: the next PR's plan comment for `infra/aws` shows no unexpected
diff on `cloudflare_dns_record.delegation`/`cloudflare_dns_record.ds`; run
`task dns-check` (`scripts/dns_check.py`) to confirm delegation and DNSSEC
still validate.

## Forwarder function key

- **Owner**: the repository owner.
- **Where it lives**: an Azure Function default host key, **not** a
  Terraform resource - `data.azurerm_function_app_host_keys.forwarder`
  (`infra/azure/alerts.tf`) reads whatever key currently exists and bakes
  it into `local.forwarder_url`
  (`https://<forwarder host>/api/alerts?code=<key>`).
- **What reads it**: the Azure Monitor action group's webhook receiver
  (`azurerm_monitor_action_group.alerts`, via `local.forwarder_url` -
  picks up a regenerated key automatically on `infra/azure`'s **next**
  apply, since the data source re-reads at apply time); the `FORWARDER_URL`
  **GitHub Environment secret** (`demo` environment) - a manually-copied
  snapshot of `terraform -chdir=infra/azure output -raw forwarder_url`,
  consumed by `estate-demo.yml` and passed to `task estate-up`, which
  renders it into the Kubernetes estate's Alertmanager route-B receiver
  (`scripts/render_alertmanager_values.py`).

**Rotation steps**: regenerate the key in the Azure Portal (Function App ->
App keys) or `az functionapp keys set --key-type functionKeys`, then:

1. Run/wait for the next `infra/azure` apply - the action group's webhook
   picks up the new key automatically (no manual step, since the data
   source is read fresh).
2. Manually update the `FORWARDER_URL` GitHub Environment secret with the
   new URL (`terraform -chdir=infra/azure output -raw forwarder_url` after
   step 1), since nothing does this automatically.

**What breaks in between**: the AWS-side Azure Monitor path (route via the
action group) is only broken until the next `infra/azure` apply - short,
and self-healing on the normal deploy cadence. The Kubernetes estate's
route B is broken until the `FORWARDER_URL` secret is updated **and**
`estate-demo.yml` (or a local `task estate-up`) next runs - potentially
until the next scheduled run (Sundays 06:00 UTC) if nobody dispatches it
by hand, since nothing currently alerts on a stale `FORWARDER_URL`.

**Verify**: `gh workflow run deploy.yml -f root=azure -f
chaos_probe=notifications-429` for the AWS-side path;
`python scripts/estate_scenarios.py --scenario cards-timeouts` (which
takes route B) or `--scenario broker-down` for the Kubernetes side, after
step 2 and a fresh `task estate-up`.
