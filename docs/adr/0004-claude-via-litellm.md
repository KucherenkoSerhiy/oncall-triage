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
