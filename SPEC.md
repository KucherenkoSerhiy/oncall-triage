# Spec: oncall-triage — a multi-role log triage workflow in Google ADK

> **Phase 1 record (local CLI, September 2026).** This document describes the
> first, laptop-only version and its recorded run on `gemini-3.5-flash-lite`.
> The deployed system runs Claude Haiku 4.5 via ADK LiteLLM
> ([ADR 0004](docs/adr/0004-claude-via-litellm.md)); see README.md for the
> current demo script.

A three-role agent workflow that triages service log errors: recognizes
previously-explained known issues, researches genuinely new ones, and
reports with a verbosity matched to the case. Python, Google ADK
(`google-adk` package), model `gemini-flash-latest`.

## Roles and flow

1. **triage** (root agent): given a request like "check payments-service
   logs", pulls logs via the `get_logs` tool and checks each error against
   the known-issues store via the `check_known` tool. Known issue → hand
   off directly to **reporter**. New issue → hand off to **researcher**
   first. Uses ADK dynamic delegation (`sub_agents`, description-driven),
   NOT a fixed SequentialAgent — the flow genuinely branches.
2. **researcher** (sub-agent): for a new error, produces a short
   characterization from the error text itself: likely cause category,
   severity guess, suggested next diagnostic step. No external services —
   reasoning only.
3. **reporter** (sub-agent): formats the final answer. Known issue → one
   terse line citing the stored explanation, no alarm. New issue → a
   fuller report: the error, researcher's characterization, and a
   recommendation to page or not.

The user can also teach the system: "the X error in service Y is expected,
because Z" → triage stores it via the `remember_issue` tool.

## Requirements

1. An ADK app package `oncall_triage/` with `root_agent` defined in
   `oncall_triage/agent.py`, runnable with `adk web` / `adk run` from the
   repo root (the standard ADK layout: `__init__.py` exposing the agent).
2. Three `Agent` roles wired exactly as above: root `triage` with
   `sub_agents=[researcher, reporter]`; researcher and reporter must have
   `description` fields that make description-driven delegation work.
3. Tools, all plain Python functions on the triage agent:
   - `get_logs(service: str) -> list[str]` — mock log store covering at
     least 3 services with a mix of known-class and new-class errors;
     unknown service returns a friendly message, never raises.
   - `check_known(error_text: str) -> dict` — looks up the known-issues
     store; returns match status plus the stored explanation when found.
   - `remember_issue(error_pattern: str, explanation: str) -> dict` —
     persists to the store.
4. Known-issues store: a local JSON file (path configurable via env var
   `TRIAGE_STORE_PATH`, default `known_issues.json` in the repo root).
   Ships pre-seeded with at least one known issue so the known-path is
   demonstrable out of the box. (Production swap-in for this store would
   be Vertex AI Memory Bank; not required here.)
5. Agent instructions must operationalize the known-vs-new decision: the
   triage instruction explicitly tells the model what to do for a known
   match vs a new error (which sub-agent to hand to and why), and the
   reporter instruction explicitly defines both output formats.
6. Tests (pytest), all passing WITHOUT any live model call or API key —
   structural/wiring tier only, mirroring: root_agent exists and is
   importable; sub_agents wiring is exactly researcher + reporter; all
   three tools are attached to triage; `get_logs` unknown-service safety;
   `check_known` hit and miss against a temp store; `remember_issue`
   persists and is then found by `check_known`; instruction content
   checks (triage instruction mentions both sub-agents' handoff
   conditions; reporter instruction defines both formats).
7. A `.env.example` with `GOOGLE_API_KEY=` placeholder; code must not
   crash on import when no key is present (tests must run keyless).
8. README.md: what it is, the role/flow description, how to run
   (`adk web`), how to run tests, and a mermaid sequence diagram of both
   paths (known and new).

## Non-requirements

No live-model integration tests (free-tier throttling makes them flaky;
they'd be added later behind a pytest marker). No real log ingestion. No
Memory Bank wiring. No deployment.
