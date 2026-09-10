# Implementation decisions (M9e)

`docs/specs/m9e-runbooks-and-demo-script.md` is precise about content and
gives verbatim run data for the rollback drill, but leaves several concrete
choices to the implementation. Recorded here rather than guessed silently.

- **The new ADR is 0017, not 0016.** The spec's requirement 7 says
  'ADR 0016 "Runbooks derived from incidents"', but M8 already shipped
  `docs/adr/0016-c4-drift-as-a-merge-gate.md` (`docs/adr/README.md`'s index
  confirms it, and `scripts/adr_index.py` regenerates that index from the
  files on disk - a duplicate 0016 would either collide on disk or silently
  drop one entry from the table). The spec text was almost certainly
  written before M8 claimed 0016. Used the next number, 0017, which is what
  the repo's own convention (`docs/adr/README.md`: "A new record is added
  whenever a decision changes; old ones are superseded, never edited")
  would produce regardless - a fresh ADR always takes the next free
  number, never a fixed one chosen in advance.
- **The cost table's DESIGN.md reference is §9, not §8.** Requirement 4
  says "the table from DESIGN section 8"; the actual cost-model table in
  the current `docs/DESIGN.md` (v2.2) is §9 ("Cost model") - §8 is
  "Security posture". Same situation as the ADR number: the section shifted
  after the spec text was written (`docs/DESIGN.md`'s own changelog shows
  a v2.1→v2.2 edit that touched §4 and §10; an earlier revision likely had
  security posture and cost model swapped or combined). `docs/runbooks/cost.md`
  cites §9, since citing a section that doesn't hold the cost table would
  send a reader to the wrong place.
- **`scripts/check_links.py`'s orphaned-view check treats "referenced" as
  "the view's key name appears in some document other than
  `docs/c4/generated/README.md` itself."** The spec says the check should
  fail on a generated C4 view "not referenced from any document" - but
  nothing in the repo links to an individual `docs/c4/generated/*.mmd` file
  by path today (the wrapper `README.md` inlines each `.mmd`'s raw content,
  it doesn't link to the file), so a literal same-path-link requirement
  would fail on the current, correct repository. Instead each generated
  file's key (`structurizr-context.mmd` → `context`, matching
  `scripts/c4_render.py`'s own `ORDER`/`TITLES` naming) must appear as text
  in some *other* document - which `docs/c4/README.md`'s "## Views"
  paragraph already satisfies for all ten current views. This still catches
  real drift: a new view exported to `generated/` that nobody's prose
  mentions anywhere fails the check (see
  `tests/scripts/test_check_links.py::test_orphaned_c4_view_is_reported`),
  and the corpus deliberately excludes the generated `README.md` itself so
  the check can't be satisfied by the view's own embedded content.
- **The console-token rotation is prepared but not executed - flagged
  explicitly as an open human follow-up, not presented as done.**
  Requirement 3 and issue
  [#31](https://github.com/KucherenkoSerhiy/oncall-triage/issues/31) (real,
  open, confirmed via `WebFetch` - title: "chore: rotate the console
  bearer token (value was visible in a screenshot during setup)", no
  comments, explicitly blocked on this runbook existing) both call for
  "actually rotat[ing] the console token as part of this slice (record the
  run)." The rotation is a Terraform `keepers` bump
  (`infra/aws/secrets.tf`) that only takes effect on the next `infra/aws`
  apply, and this builder has no cloud credentials to trigger or observe
  that apply (the repository's own model is "PR produces a plan, merging
  applies it" - Terraform applies are human/CI-triggered, never something a
  dev-loop agent runs directly, same as every other infra change in this
  repo). Unlike the rollback drill (whose run ids and timestamps were
  supplied verbatim by the operator because that drill already happened),
  no run for this rotation exists yet - and inventing one, or wording the
  runbook to imply it already happened, would be worse than the gap itself.
  Shipped the code-level requirement in full (the `keepers` bump) and
  `docs/runbooks/secrets-rotation.md`'s "Console token" section now states
  plainly ("Rotation status: prepared, not yet executed") that closing #31
  needs a human to merge, dispatch `deploy.yml -f root=aws` (or `all`), and
  fill in a specific empty table row with the real run id/timestamps/smoke
  output - the same format the rollback drill uses - rather than treating
  the Terraform change alone as satisfying "record the run."
- **The rollback drill's before/after `CodeSha256` gap is closed with a
  verified secondary source, not the literal `diagnose.yml` reading the
  spec asks for.** The spec wants "the before/after `CodeSha256` from
  `diagnose.yml`," but the operator's own recorded drill data doesn't
  include it (nobody ran `diagnose.yml` during the drill), and this builder
  has no AWS credentials to read the live Lambda's `CodeSha256` after the
  fact either. What *is* available offline: this repository is real and
  public, so `WebFetch` against the actual `github.com` Actions run pages
  for the rollback (`34437783068`), the roll-forward
  (`34438448931`, whose own `image` job pushes and reports the digest for
  `sha-5ed015b` directly since HEAD was at that commit), and - found by
  tracing PR [#65](https://github.com/KucherenkoSerhiy/oncall-triage/pull/65)'s
  merge commit `d7b0932` to the `deploy.yml` push run it triggered
  (`34425871044`) - the original build of `sha-d7b0932`, all return real,
  independently-checkable image-manifest digests for the exact tags this
  drill moved between. `docs/runbooks/deploy-and-rollback.md` now carries
  those two digests in a table, sourced and linked to each run, labelled
  precisely for what they are (the pushed image's manifest digest, which
  is what AWS derives a container-image Lambda's `CodeSha256` from) rather
  than conflated with a literal `aws lambda get-function-configuration`
  reading nobody took. This is real, verifiable, non-fabricated evidence
  that the image actually changed and changed back - strictly stronger
  than the "run it yourself next time" promise the spec explicitly said
  not to leave - but it is one hop short of the exact artifact requested,
  and the runbook says so rather than blurring the two together. (One
  caveat worth naming: the digest strings themselves were transcribed off
  dynamically-rendered GitHub pages by `WebFetch`'s own summarization
  model, not copied byte-for-byte from an API response - each parses as a
  well-formed 64-hex-character SHA256, and three independent fetches
  produced three distinct, non-boilerplate values, but a single flipped
  hex character from that transcription step can't be fully ruled out
  without an independent read.)
- **M9d and M9e's own issue numbers (#29, #30).** Not given verbatim in
  the spec's "Inputs" section (only #26-#28 and #81 are named explicitly for
  M9a-c). The existing README roadmap row for M9 already named the range
  "#27-#30" for M9b-M9e before this slice, which only resolves to #29 for
  M9d and #30 for M9e if the milestone-to-issue mapping is sequential
  (#26=M9a, #27=M9b, #28=M9c, #29=M9d, #30=M9e) - consistent with every
  other milestone in this repo having exactly one issue per lettered slice.
  Used that mapping in the roadmap table and the reviewer-list citations.
- **`docs/runbooks/cost.md`'s dollar figures are the DESIGN.md model,
  refreshed against what's actually deployed today (e.g., `enable_dnssec`'s
  live default), not a pulled AWS Cost Explorer / Azure Cost Management
  total.** The spec explicitly doesn't require screenshots but does say
  "numbers are [required]"; this builder has no network access to either
  cloud's billing API (an offline-only environment, like every other gate
  in this repo), so there is no live invoice figure to substitute. The
  runbook says so plainly ("Reconciling against real billing") rather than
  presenting a modelled number as if it were an observed one, and the "one
  month later" checklist makes pulling the real total the first, explicit,
  human step.
