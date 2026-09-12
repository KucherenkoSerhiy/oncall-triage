# Demo — teach it once, it never pages you for that again

> **Phase 1 record (local CLI, September 2026).** This document describes the
> first, laptop-only version and its recorded run on `gemini-3.5-flash-lite`.
> The deployed system runs Claude Haiku 4.5 via ADK LiteLLM
> ([ADR 0004](docs/adr/0004-claude-via-litellm.md)); see README.md for the
> current demo script.

Three acts, one command, ~90 seconds. Uses an isolated store copy so
the repo's seeded `known_issues.json` is never modified.

```bash
./demo.sh
```

What it does (and what actually happened on the recorded live run,
2026-09-02, `gemini-3.5-flash-lite`):

**Act 1 — a new error gets researched.** "check inventory-service
logs" → the connection-pool error is recognized as known (seeded), and
the StockReconciliationTimeout is new → researched and reported.

**Act 2 — teach it.** One natural-language sentence:

> The StockReconciliationTimeout in inventory-service is expected:
> warehouse-sync-3 runs a nightly batch that pauses reconciliation.
> Not an incident, please remember this.

Live response:

> [triage]: I have successfully recorded that the
> `StockReconciliationTimeout waiting on warehouse-sync-3` error in
> `inventory-service` is expected due to the nightly batch run, and it
> has been added to the known-issues store.

**Act 3 — same question again.** The error that triggered research in
Act 1 now short-circuits:

> [reporter]: Known issue: StockReconciliationTimeout waiting on
> warehouse-sync-3 - warehouse-sync-3 runs a nightly batch that pauses
> reconciliation. Not an incident.

And the store file proves it persisted (this is the actual diff from
the recorded run):

```json
{
  "issues": [
    { "pattern": "connection pool exhausted", "explanation": "Known scaling limit ..." },
    { "pattern": "StockReconciliationTimeout waiting on warehouse-sync-3",
      "explanation": "warehouse-sync-3 runs a nightly batch that pauses reconciliation. Not an incident." }
  ]
}
```

Because the store is on disk, Act 3 works equally well after a full
process restart — that's the point: suppression knowledge that
survives, taught in plain language, no rule DSL.

## Why this is worth showing

The un-wow way to get this behavior is a rules engine and a config
review. Here the on-call engineer says "that's expected, remember it"
in the middle of handling an alert, and the system routes every future
occurrence to the terse path — while genuinely new errors still get
researched and fully reported. Explain-once memory as the suppression
mechanism is the differentiator the market research flagged as absent
from existing tooling (see `C:\repos\research\2. oncall-memory-triage-market-research.md`).
