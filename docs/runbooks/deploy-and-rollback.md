# Runbook: deploy and rollback

## How a change flows

1. **PR opens** touching `infra/aws/**`, `infra/aws-ecr/**`, `infra/azure/**`,
   `infra/modules/**`, `services/**`, `bank/aws/**`, `oncall_triage/**`, or
   the probe scripts. `deploy.yml`'s `plan` job runs `terraform plan` for
   both `infra/aws` and `infra/azure` and posts the diff as a PR comment (one
   comment per root, updated in place on every push - look for `<!--
   tfplan:aws -->` / `<!-- tfplan:azure -->`). Read it before approving;
   this is the only place a reviewer sees exactly what will change.
2. **Merge to `master`** re-runs `plan`, then `apply` waits for the **`demo`
   GitHub Environment's required reviewer approval** - the first of the two
   approval legs.
3. **`apply` runs** (AWS, then Azure - `max-parallel: 1` in the matrix, so
   Azure's plan/apply steps can read AWS's fresh SSM values for
   `console_token`/`ingest_hmac_secret`), each still gated by the same
   `demo` environment, which is the **second** approval leg in practice: a
   `workflow_dispatch` re-run of `apply` (a rollback, say) asks for approval
   again even though the PR that introduced the code was already approved
   once at merge time. Two distinct clicks, two distinct purposes - "this
   diff is right" at merge, "this specific apply, right now, is intended" at
   dispatch.
4. **`smoke` runs** after `apply` succeeds: `scripts/smoke.py` fires one
   synthetic alert and polls for a verdict (\<= 90 s), then a non-fatal DNS
   check, then - only on `workflow_dispatch` with `chaos_probe` set - one
   real alarm end to end via `scripts/chaos_probe.py`.

## The concurrency group, and why a dispatch can queue

```yaml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false
```

Grouped **per ref**, not globally: a PR's plan runs on `refs/pull/<n>/merge`
and never blocks (or is blocked by) `master`'s apply. But two events on the
*same* ref - a push to `master` and, minutes later, a `workflow_dispatch`
rollback also targeting `master` (the default branch is implied when no
different ref is picked in the Actions UI) - share a group, and
`cancel-in-progress: false` means the second waits in `queued` for the first
to finish rather than cancelling it. This is deliberate: both runs touch the
same Terraform state, so `plan`/`apply` would otherwise fight over the state
lock and fail loudly instead of just queueing quietly. Practical
consequence: if a rollback needs to happen *right now* and a routine
`master` deploy is already mid-run, the rollback dispatch queues behind it
rather than racing it - check the Actions tab for an already-running
`deploy` on the same ref before assuming a new dispatch is stuck.

## The two approval legs

Both legs are the same GitHub Environment (`demo`, one required reviewer),
but they gate different things:

| Leg | Gates | What you're actually approving |
|---|---|---|
| Merge -> `apply` | Every push to `master` | The code + Terraform diff already reviewed in the PR - "this is the change I want live" |
| `workflow_dispatch` -> `apply` | Every manual dispatch (rollback, Anthropic key rotation via `anthropic_key`, a re-run) | The specific action this dispatch requests, independent of whether the underlying code changed - "yes, roll back to `sha-<previous>` right now" |

There is no way to skip either leg from the Actions UI; the rollback drill
below shows both being clicked.

## What "Verify the Function apps" guards

`deploy.yml`'s `apply` job, Azure leg only, right after `terraform apply`:

```yaml
- name: Verify the Function apps indexed their functions
  if: steps.sel.outputs.run == 'true' && matrix.root == 'azure'
  run: |
    for app in nordwind-triage-demo-notifications nordwind-triage-demo-forwarder; do
      # az functionapp function list, retried for up to 5 minutes
```

A zip deploy to an Azure Function app can report success while the app ends
up exposing **zero** functions - a missing dependency in `requirements.txt`,
or a build mode that skips Oryx's remote build entirely
(`WEBSITE_RUN_FROM_PACKAGE=1`, which is exactly what left
`azure-monitor-opentelemetry` missing and the timer trigger unindexed the
first time this happened -
[#59](https://github.com/KucherenkoSerhiy/oncall-triage/issues/59)). Without
this step, that failure mode is invisible until the next chaos probe or
Azure Monitor alert silently never fires
([#64](https://github.com/KucherenkoSerhiy/oncall-triage/issues/64)) - an
hour or more later, with no clue which of the two apps is broken. The step
polls `az functionapp function list` every 15 s for up to 5 minutes (the
app needs time to finish indexing after a cold deploy) and fails the
**apply job itself** the moment either app comes up empty, turning a
silent, delayed failure into an immediate, attributable one.

## The rollback drill

Rollback redeploys a **previously built, already-verified** worker image by
SHA - images are immutable and tagged `sha-<git sha>` (`infra/README.md`
"Rollback"), so nothing is rebuilt, only re-pointed:

```bash
gh workflow run deploy.yml -f root=aws -f worker_image_sha=sha-<previous>
```

`image` still runs (it always does on `workflow_dispatch`) and pushes the
*current* commit's image too, but the explicit `worker_image_sha` input
wins in both the `plan` and `apply` jobs' "Determine the worker_image_sha
var" step, so the Lambda ends up pointed at the older image regardless.
Verify with `bankops fire` (or a chaos probe) plus the console; roll forward
the same way, with the SHA that was live before the drill.

### Recorded: 2026-09-10 (UTC)

Worker image before the drill: `sha-5ed015b` (the `master` HEAD at the
time). Rolled back to `sha-d7b0932` (the image built for
[#65](https://github.com/KucherenkoSerhiy/oncall-triage/pull/65)) with:

```bash
gh workflow run deploy.yml -f root=aws -f worker_image_sha=sha-d7b0932
```

| Step | Run | Started | Finished | Result | Smoke |
|---|---|---|---|---|---|
| Rollback to `sha-d7b0932` | [34437783068](https://github.com/KucherenkoSerhiy/oncall-triage/actions/runs/34437783068) | 04:35:38Z | 04:45:54Z | success (both approval legs) | `OK: alert_id=01M24T4HR7WY5FQT9RAEJ9C3M9 action=monitor; known_alert_id=01M24T5GJTPE8QA5N1EZBWJK34` |
| Roll forward to `master` (`sha-5ed015b`) | [34438448931](https://github.com/KucherenkoSerhiy/oncall-triage/actions/runs/34438448931) | 04:46Z | 04:55:52Z | success | `OK: alert_id=01M24TP2S7R2XD8GTJMNTJN879 action=monitor; known_alert_id=01M24TQ69P7K9ZDK2JSJHGX6BY` |

**Time from decision to a verified rollback: ~10 minutes**, dominated by the
`image` job (skipped - "already in ECR" - since `sha-d7b0932` had already
been pushed for #65) and the two approval clicks, not by any Terraform work
(the AWS apply itself only changes the Lambda's `image_uri`).

**Before/after state**: `diagnose.yml`'s "Account concurrency + worker
configuration" step prints the worker's `CodeSha256` (the deployed image's
digest, not the git SHA) from `aws lambda get-function-configuration` -
that's the mechanism to reach for on the *next* rollback, run before and
after to watch the value change directly against the live Lambda. Nobody
ran `diagnose.yml` during this drill, so there's no `CodeSha256` reading
taken directly from the Lambda for it - but each image tag's own manifest
digest, from the `image` job of the `deploy.yml` run that actually pushed
it, is a real, independently-checkable stand-in for the same fact (the
worker's container image, which is what `CodeSha256` hashes, changed and
changed back to a specific, named value) - not a promise to check later:

| State | Image tag | `deploy.yml` run that pushed it | Image manifest digest |
|---|---|---|---|
| Before the drill (rolled back to) | `sha-d7b0932` | [34425871044](https://github.com/KucherenkoSerhiy/oncall-triage/actions/runs/34425871044) (the push from merging [#65](https://github.com/KucherenkoSerhiy/oncall-triage/pull/65)) | `sha256:6918e0662108b3319aad4aa5fcaa187be4fa18cd803ab722d92e1644f4d332e3` |
| After (rolled forward to) | `sha-5ed015b` | [34438448931](https://github.com/KucherenkoSerhiy/oncall-triage/actions/runs/34438448931) (the roll-forward run itself) | `sha256:a84a9da7eb5ebae64d2871a19f2608f0f131fdc07edac220f712e3398e81eef7` |

Two different digests, confirming the rollback drill actually moved the
deployed image and moved it back - not two runs that happened to agree.
This is one hop short of the spec's exact ask: `image_uri` (and therefore
Lambda's own `CodeSha256`, which AWS derives from the same pushed image)
is what the Terraform apply actually sets, but nobody captured the Lambda
API's own `CodeSha256` reading at drill time to confirm AWS recomputed it
identically - that confirmation needs `diagnose.yml` run live, with AWS
credentials, which this documentation pass doesn't have. Treat the table
above as strong secondary evidence, and the next rollback drill as the
chance to record the primary one.

## Chaos probe as the deploy-time proof

`deploy.yml`'s `chaos_probe` dispatch input (`payments-pool`,
`payments-errors`, `ledger-lag`, `auth-jwks`, `notifications-429`) is the
closest thing to a canary: it runs after `smoke` on the same run, driving
one real cloud alarm end to end rather than the synthetic `bankops fire`
path smoke uses. Every milestone from M4 on recorded its live probe this
way, including the M9e deploy that carries this PR - see
[`docs/runbooks/secrets-rotation.md`](secrets-rotation.md#console-token) for
that run's details, since it's also the console-token rotation.
