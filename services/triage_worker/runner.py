"""Runs the ADK triage agent tree for a single alert.

The model seam lives here: ``TriageRunner(agent_factory=...)`` defaults to
the real ``root_agent`` (Claude via LiteLLM, see ``oncall_triage/model.py``),
but tests pass a factory that builds an agent tree wired to a scripted fake
``BaseLlm`` instead - see ``tests/triage_worker/fake_llm.py``. No test ever
constructs the default factory, so no test ever calls a model.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

_APP_NAME = "nordwind-triage"
_USER_ID = "oncall"
_VERDICT_RE = re.compile(r"```verdict\s*\n(.*?)\n```\s*$", re.DOTALL)
_REQUIRED_VERDICT_KEYS = {"known", "severity", "action", "summary"}


@dataclass
class TriageResult:
    text: str
    verdict: dict[str, Any]
    model: str
    prompt_hash: str
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    verdict_parse_error: bool = False


def _default_agent() -> Agent:
    from oncall_triage.agent import root_agent

    return root_agent


def _model_string(agent: Agent) -> str:
    model = agent.model
    return model.model if hasattr(model, "model") else str(model)


def _prompt_hash(agent: Agent) -> str:
    instructions = [str(agent.instruction)]
    instructions.extend(str(sub.instruction) for sub in agent.sub_agents if isinstance(sub, Agent))
    return hashlib.sha256("".join(instructions).encode()).hexdigest()


def _parse_verdict(text: str, fallback_severity: str) -> tuple[dict[str, Any], bool]:
    match = _VERDICT_RE.search(text.strip())
    if match is not None:
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and data.keys() >= _REQUIRED_VERDICT_KEYS:
            return data, False

    return {
        "known": False,
        "severity": fallback_severity,
        "action": "monitor",
        "summary": text[:200],
    }, True


class TriageRunner:
    def __init__(self, agent_factory: Callable[[], Agent] = _default_agent) -> None:
        self._agent_factory = agent_factory

    def run(self, alert: dict) -> TriageResult:
        agent = self._agent_factory()
        session_service = InMemorySessionService()
        session_id = f"alert-{alert['alert_id']}"
        session_service.create_session_sync(
            app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
        )

        runner = Runner(agent=agent, app_name=_APP_NAME, session_service=session_service)
        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Triage alert {alert['alert_id']}: {alert['title']}")],
        )

        text = ""
        input_tokens = 0
        output_tokens = 0
        for event in runner.run(user_id=_USER_ID, session_id=session_id, new_message=message):
            if event.usage_metadata is not None:
                input_tokens += event.usage_metadata.prompt_token_count or 0
                output_tokens += event.usage_metadata.candidates_token_count or 0
            if event.content and event.content.parts:
                part_text = "".join(part.text for part in event.content.parts if part.text)
                if part_text:
                    text = part_text

        verdict, verdict_parse_error = _parse_verdict(text, alert.get("severity", "sev3"))
        return TriageResult(
            text=text,
            verdict=verdict,
            model=_model_string(agent),
            prompt_hash=_prompt_hash(agent),
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
            verdict_parse_error=verdict_parse_error,
        )
