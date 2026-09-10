# 0017. Runbooks derived from incidents

- Status: accepted
- Date: 2026-09-10
- Design reference: docs/DESIGN.md §6.5 ("Runbooks in `docs/runbooks/`")

## Context

`docs/runbooks/` existed from M6b (`kubernetes-estate.md`) but nothing said what a runbook *is* in this repository, or where its content should come from. The obvious failure mode for a runbook written speculatively - "here's what we'd do if X happened" - is that it describes a failure mode that looks plausible but never actually occurred, while the failure modes that *did* happen (a KMS-encrypted SNS topic silently dropping every CloudWatch notification, `#47`; a real alarm payload's `Trigger.Threshold: 1.0` crashing ingest on a float DynamoDB refuses, `#50`; two deploys inside the dedup window absorbing each other's smoke alert, `#38`/`#71`) go undocumented because they were "just bugs", fixed in a PR and forgotten. A reviewer - or a future on-call engineer - reading a runbook full of hypothetical scenarios has no way to tell which sentence is backed by something that happened and which is a guess.

## Decision

Every section of `docs/runbooks/triage-spine.md`, `deploy-and-rollback.md` and `secrets-rotation.md` that names a "likely cause" cites the GitHub issue that incident was filed and fixed under, the same way `.checkov.yaml` skips and `docs/c4/drift-allow.yaml` entries each carry a reason. The rollback drill in `deploy-and-rollback.md` and the console-token rotation in `secrets-rotation.md` go further: they record a real, once-run drill (timestamps, run links, before/after state) rather than describing the mechanism in the abstract - `docs/runbooks/cost.md` is the one runbook in this set without an incident to cite, since it derives from the (accurate) DESIGN.md cost model plus a live month's numbers, not a fixed bug.

The rule going forward: when a new incident closes, the fix lands in code as usual, but if it changed what an on-call engineer would need to know to recognise or resolve the *symptom* - not just the root cause - the relevant runbook gains a section (or a row) citing that issue, added before the issue itself is closed. A runbook section with no citation is either genuinely mechanism-only (rollback's `gh workflow run` syntax, `cost.md`'s dollar table) or a sign the section was speculative and should be checked against reality before it ships.

## Consequences

The runbooks read like an incident log with the noise filtered out rather than a generic on-call handbook, which is both their value (every "likely cause" is something that already fooled someone) and their limit (a failure mode nobody has hit yet has no section - `triage-spine.md`'s "likely causes" lists are a floor, not an exhaustive fault tree). `scripts/check_links.py` (M9e) keeps the citations honest only at the link level - it cannot verify an issue number actually matches the incident described, so a wrong citation is a review-time catch, not a CI one.
