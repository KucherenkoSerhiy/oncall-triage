# Implementation decisions (M9d)

The M9d spec (`docs/specs/m9-hardening.md` requirement 5, slice 4/5) leaves
several concrete choices to the implementation. Recorded here rather than
guessed silently.

- **`infra/bootstrap/github` gets its own S3-backed state**, unlike
  `bootstrap/aws`/`bootstrap/azure` (local state, kept on whichever machine
  last applied them). The spec says so explicitly ("state in the same S3
  bucket under bootstrap/github.tfstate"), and it makes sense here
  specifically: `bootstrap/aws`'s and `bootstrap/azure`'s outputs become
  GitHub repository variables set once by hand, so a second machine never
  needs their state to keep working even across a rare re-apply like this
  one; `bootstrap/github` instead holds resources (environment protection
  rules) that get revisited more casually - adding a second reviewer, say
  - and remote state means whoever does that next does not need the
  original operator's laptop state file.
- **The immutable-subject federated credentials
  (`infra/bootstrap/azure/main.tf`'s `github_immutable` resource) keep a
  `#checkov:skip=CKV_AZURE_249`, even though the spec says retiring the
  `pull_request` credential makes "the `#checkov:skip=CKV_AZURE_249` line
  go away and checkov passes on its own."** Verified directly (`checkov -d
  infra/bootstrap/azure --check CKV_AZURE_249` with the skip line
  temporarily deleted): all four immutable-subject credentials fail even
  though every one of them is pinned to a `ref` or `environment` claim -
  the same subject shapes the four *classic*-form credentials pass
  unskipped. The cause is upstream, not this Terraform: checkov's
  `CKV_AZURE_249` (`checkov/terraform/checks/resource/azure/
  GithubActionsOIDCTrustPolicy.py`) validates the repo segment of a `repo:`
  subject against `gh_repo_regex` in `checkov/common/util/oidc_utils.py`
  (`(\$\{)?[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)*(\})?/[^/]+`, checkov 3.3.16,
  installed version as of 2026-09-10). That character class has no `@`, so
  it cannot match GitHub's immutable subject's owner/repo segment
  (`owner@ownerId/repo@repoId`) at any position - the check fails on repo
  *format* alone, before it ever looks at what claim (`pull_request`,
  `ref`, `environment`) follows. The regex predates GitHub's April 2026
  immutable-subject-claims rollout and has not been updated for it
  (checked against the installed package; no local patch is available).
  Two ways to make the skip fully disappear were rejected: (a) drop the
  immutable subject and keep only the classic one - not an option, this
  repository issues the immutable subject unconditionally per ADR 0008's
  2026-09-09 amendment, so every push/apply to `master`/`demo` would lose
  Azure OIDC auth entirely; (b) reshape the Terraform so the check parses
  the subject differently - not possible, the check reads the literal
  `subject` argument's value, which must equal the exact string GitHub's
  OIDC token issues (not a Terraform-side construction choice). Also
  checked whether a newer checkov release already fixes this: downloaded
  and inspected `checkov==3.3.17` (the latest release on PyPI as of
  2026-09-10, one version ahead of the `3.3.16` this repo's tooling has
  installed) directly from its wheel - `checkov/common/util/oidc_utils.py`
  ships the byte-identical `gh_repo_regex`, so upgrading buys nothing. So
  the skip survives, scoped to only the four immutable-subject credentials
  (split into their own `github_immutable` resource specifically so the
  four classic-subject ones do not inherit it), with the reason changed
  from "pull_request subject, planned for M9" to "checkov's own repo-
  format regex rejects the immutable subject shape, independent of claim
  type" - an upstream tool limitation, not a residual policy exception for
  this credential's actual scope. Filing this against
  `bridgecrewio/checkov` is a follow-up outside this slice (no cloud
  credential needed for it, unlike the rest of M9d).
  **This means requirement 2's literal text - "the `#checkov:skip=
  CKV_AZURE_249` line goes away and checkov passes on its own" - is not
  met for these four credentials with any checkov release that exists
  today**; the skip is the smallest one possible (4 of 8 credentials, not
  the original 8 of 8) and is scoped to a verified, cited upstream defect
  rather than the M9d subject change itself, but closing this gap for real
  needs either an upstream checkov release or the spec owner accepting
  this documented deviation - both outside what a Terraform/CI change in
  this repository can do.
- **`plan_environment` is a variable (default `"plan"`), not a literal**,
  in both `bootstrap/aws` and `bootstrap/azure` - mirrors the existing
  `environment` variable (default `"demo"`) the trust policies already use,
  rather than hardcoding a second magic string next to it.
- **The `demo` environment is imported, not recreated.** It already exists
  (created by hand before `infra/bootstrap/github` existed, per
  `infra/README.md`'s original Bootstrap section). `terraform import
  github_repository_environment.demo oncall-triage:demo` brings it under
  management without a destroy/recreate cycle that would momentarily drop
  its required-reviewer protection.
- **The personal-repository reviewer fallback is documented, not coded as
  a Terraform conditional.** Whether `integrations/github`'s `reviewers`
  block succeeds on a non-organization repository can only be known by
  actually running `terraform apply` with a real token - not knowable
  offline, and not worth an untestable `try`/feature-flag in the module
  itself. `infra/README.md` documents the fallback (drop the `reviewers`
  block, apply again, set the reviewer by hand once) as an operator
  runbook step instead.
- **Requirements 4 and 6 conflict on `diagnose.yml`, and `tests/
  test_workflows.py` documents that conflict instead of silently resolving
  it.** Requirement 6 says the test "asserts every job that assumes a
  cloud role declares an environment"; requirement 4 says `estate-demo.yml`
  and `diagnose.yml` are "unchanged (they already run in demo)". That
  premise is false for `diagnose.yml`: its one job (`aws`) has never
  declared `environment: demo` - checked directly against the file, not
  assumed. So requirement 6 read literally would force adding
  `environment: demo` to `diagnose.yml`, which requirement 4 explicitly
  forbids. **Flagging this for the spec owner to reconcile** (the spec is
  a read-only contract here, not something this slice can silently edit
  either direction). Pending that, the test does not special-case whole
  files - every job in all three workflow files is inspected
  unconditionally (`test_every_cloud_role_job_declares_an_environment_or_
  is_a_named_exception`) - but a small, explicitly named, closed list of
  currently-known non-declaring jobs is allowed to survive
  (`_UNDECLARED_BUT_UNREACHABLE`: `diagnose.yml:aws` plus `deploy.yml`'s
  `ecr`/`image`/`anthropic_key`/`smoke`, all `workflow_dispatch`/`push`-
  only). A second test
  (`test_named_environment_exceptions_are_actually_pull_request_
  unreachable`) asserts every one of those named jobs is genuinely
  unreachable from a `pull_request` event - the actual security property
  M9d narrows, since only that reachability lets a job present the bare,
  unscoped `pull_request` subject M9d retires. A third test keeps the
  original PR-reachability assertion directly (`test_jobs_reachable_from_
  pull_request_scope_their_oidc_subject_to_an_environment`). The net
  effect: nothing is skipped by filename any more, every exception is
  named and independently re-verified as safe, and the one requirement-4-
  vs-6 gap left open (`diagnose.yml:aws`) is a visible, deliberate,
  documented line in the test file rather than an implicit file-level
  skip.
- **The PR template gets one added checklist line, not a second template
  file.** The spec's "PR template asks for it" is satisfied by a
  conditional checklist item (paste the plan output if this PR touches
  `infra/bootstrap/*`, otherwise n/a) rather than a
  `PULL_REQUEST_TEMPLATE/bootstrap.md` variant, since bootstrap changes are
  rare enough that a second template to discover and choose between would
  be more friction than the one extra line.
