"""M9d gate (docs/specs/m9-hardening.md requirement 6): parses the three
workflow files and asserts every job that assumes a cloud role declares a
GitHub Actions environment (`plan` or `demo`).

Read fully literally, that would also flag `diagnose.yml`'s `aws` job,
which assumes the AWS role but declares no `environment:` - even though
requirement 4 says `diagnose.yml` is "unchanged (they already run in
demo)". That premise does not hold: `diagnose.yml`'s `aws` job has never
declared `environment: demo` (checked directly against the file - see
`_UNDECLARED_BUT_UNREACHABLE` below), so requirements 4 and 6 conflict for
this one job - requirement 6 taken literally would require editing a file
requirement 4 says not to touch. Flagged for the spec owner to reconcile
(docs/DECISIONS.md has the full note) rather than silently resolved by
picking one requirement over the other.

Pending that reconciliation, this module still checks every job in all
three files (nothing is skipped file-by-file): a job is required to
declare `plan`/`demo` unless it is *structurally* unreachable from a
`pull_request` event - either its workflow has no `pull_request` trigger
at all, or its own `if:` condition excludes that event. That is the actual
security property M9d narrows (the bare, unscoped `pull_request` OIDC
subject, reachable from any PR), and it is untouched by which requirement
"wins": a job that cannot run from a pull_request cannot present that
subject regardless of whether it declares an environment. The one
non-declaring survivor this currently allows,
`diagnose.yml:aws` (workflow_dispatch-only), is enumerated explicitly and
re-checked by name below so a future job silently joining it would still
have to earn its way onto the list, not just avoid the file-level filter
this test previously used.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATHS = [
    REPO_ROOT / ".github/workflows/deploy.yml",
    REPO_ROOT / ".github/workflows/estate-demo.yml",
    REPO_ROOT / ".github/workflows/diagnose.yml",
]

CLOUD_LOGIN_ACTIONS = ("aws-actions/configure-aws-credentials", "azure/login")
ALLOWED_ENVIRONMENTS = {"plan", "demo"}

# Cloud-role jobs known today to declare no environment. Every one of them
# must also be unreachable from `pull_request` (asserted below by name) -
# this is not a blanket exemption, it is a closed, reviewed list. Adding a
# job here without it actually being pull_request-unreachable is caught by
# test_named_environment_exceptions_are_actually_pull_request_unreachable.
_UNDECLARED_BUT_UNREACHABLE = {
    # requirement 4: diagnose.yml is unchanged by M9d. Its only trigger is
    # workflow_dispatch, so its OIDC subject is `ref:refs/heads/<branch>`
    # (accepted by both trust policies unconditionally) - never the bare
    # `pull_request` subject M9d retires, since the workflow has no
    # pull_request trigger to reach it from.
    (".github/workflows/diagnose.yml", "aws"),
    # requirement 4: deploy.yml's own non-plan/apply/smoke jobs run only on
    # push/workflow_dispatch (`if: ... != 'pull_request'`); each carries the
    # same ref-scoped subject as a push to master, not the retired one.
    (".github/workflows/deploy.yml", "ecr"),
    (".github/workflows/deploy.yml", "image"),
    (".github/workflows/deploy.yml", "anthropic_key"),
    (".github/workflows/deploy.yml", "smoke"),
}


def _load_workflow(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # PyYAML (YAML 1.1) reads the bare `on:` key as the boolean True.
    data.setdefault("on", data.pop(True, {}))
    return data


def _triggers(workflow: dict) -> set[str]:
    on = workflow.get("on", {})
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on.keys())
    return set()


def _assumes_cloud_role(job: dict) -> bool:
    return any(
        str(step.get("uses", "")).startswith(CLOUD_LOGIN_ACTIONS)
        for step in job.get("steps", []) or []
    )


def _excludes_pull_request(job: dict) -> bool:
    condition = str(job.get("if", ""))
    return "pull_request" in condition and ("!=" in condition or "!" in condition)


def _environment_name(job: dict) -> str | None:
    environment = job.get("environment")
    if isinstance(environment, str):
        return environment
    if isinstance(environment, dict):
        return environment.get("name")
    return None


def _pull_request_reachable(workflow: dict, job: dict) -> bool:
    return "pull_request" in _triggers(workflow) and not _excludes_pull_request(job)


def _cloud_role_jobs():
    """Yields (relative_path, job_name, workflow, job) for every job in the
    three workflow files that assumes a cloud role - every file, every job,
    nothing pre-filtered."""
    for path in WORKFLOW_PATHS:
        workflow = _load_workflow(path)
        for job_name, job in workflow.get("jobs", {}).items():
            if _assumes_cloud_role(job):
                yield path.relative_to(REPO_ROOT).as_posix(), job_name, workflow, job


def test_every_cloud_role_job_declares_an_environment_or_is_a_named_exception():
    violations = []
    for rel_path, job_name, _workflow, job in _cloud_role_jobs():
        if _environment_name(job) in ALLOWED_ENVIRONMENTS:
            continue
        if (rel_path, job_name) in _UNDECLARED_BUT_UNREACHABLE:
            continue
        violations.append(f"{rel_path}:{job_name}")

    assert not violations, (
        "jobs assume a cloud role without declaring environment: plan or demo, "
        f"and are not a named, justified exception: {violations}"
    )


def test_named_environment_exceptions_are_actually_pull_request_unreachable():
    """Every job in _UNDECLARED_BUT_UNREACHABLE must genuinely be unreachable
    from a pull_request event - otherwise it would present the bare,
    unscoped `pull_request` OIDC subject M9d retires."""
    reachable = []
    seen = set()
    for rel_path, job_name, workflow, job in _cloud_role_jobs():
        key = (rel_path, job_name)
        if key not in _UNDECLARED_BUT_UNREACHABLE:
            continue
        seen.add(key)
        if _pull_request_reachable(workflow, job):
            reachable.append(f"{rel_path}:{job_name}")

    assert not reachable, f"named exceptions are reachable from pull_request: {reachable}"
    missing = _UNDECLARED_BUT_UNREACHABLE - seen
    assert not missing, f"named exceptions no longer exist in the workflows: {missing}"


def test_jobs_reachable_from_pull_request_scope_their_oidc_subject_to_an_environment():
    violations = []
    for rel_path, job_name, workflow, job in _cloud_role_jobs():
        if not _pull_request_reachable(workflow, job):
            continue
        if _environment_name(job) not in ALLOWED_ENVIRONMENTS:
            violations.append(f"{rel_path}:{job_name}")

    assert not violations, (
        "jobs reachable from a pull_request event assume a cloud role without "
        f"declaring environment: plan or demo: {violations}"
    )
