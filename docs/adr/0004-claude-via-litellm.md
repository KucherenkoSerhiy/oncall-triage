# 0004. Triage agents run on Claude Haiku 4.5 through ADK's LiteLLM adapter

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D4

## Context

Phase 1 used gemini-3.5-flash-lite on the free tier, which is chronically 503-saturated. The agents are Google ADK; switching frameworks would throw away the working three-role workflow.

## Decision

Keep ADK; set LiteLlm(model="anthropic/claude-haiku-4-5-20251001"). Model id and prompt-template hash are stored on every verdict.

## Consequences

Roughly $2-3 per month at demo volume, billed by Anthropic outside the cloud budget; a per-day alert cap in the worker bounds the worst case; swapping models is a one-line change.

## Amendment (M3a): the model seam

`oncall_triage/model.py` exposes a single `build_model()` function, called
once by `agent.py` at import: `LiteLlm(model=os.environ.get("TRIAGE_MODEL",
"anthropic/claude-haiku-4-5-20251001"))`. That's the one place a model gets
constructed - `TRIAGE_MODEL` overrides it without touching code, and it's
the seam the test suite replaces: `services/triage_worker/runner.py`'s
`TriageRunner` takes an `agent_factory`, and every test passes one that
builds an agent tree against a scripted fake `BaseLlm`
(`tests/triage_worker/fake_llm.py`) instead of the real, Claude-backed
`root_agent`. No test in the repo ever calls `build_model()` for a live
model or reaches the network.
