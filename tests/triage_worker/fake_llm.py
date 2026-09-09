"""Test helper: a scripted BaseLlm fake so ADK/TriageRunner tests never call a model.

Pattern:

    fake = FakeLlm(responses=[
        tool_call_response("get_alert", {"alert_id": "A1"}),
        tool_call_response("check_known", {"service": "payments-service", "error_text": "..."}),
        transfer_response("reporter"),
        text_response('Known issue: ...\\n```verdict\\n{"known": true, ...}\\n```'),
    ])
    tree = build_scripted_agent_tree(fake)
    runner = TriageRunner(agent_factory=lambda: tree)
    result = runner.run(alert)

``responses`` is a fixed queue popped one-per-model-turn. All three agents
in the scripted tree share the same ``fake`` instance (mirroring how
``oncall_triage/agent.py`` calls ``build_model()`` once for triage,
researcher and reporter), so the queue must list turns in the order ADK
will ask for them: triage's tool calls, then its transfer, then whichever
agent it transferred to.

``fake.calls`` records every ``LlmRequest`` sent to the model, in order.
Use ``function_responses_in(fake.calls[-1])`` to see what a real tool
actually returned on a given turn - proof the tool ran, not just that a
call to it was scripted.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from oncall_triage.tools import check_known, get_alert, get_recent_alerts, remember_issue


class FakeLlm(BaseLlm):
    """Replays a fixed queue of canned ``LlmResponse``s, one per model turn."""

    model: str = "fake-1"
    responses: list[LlmResponse]
    _index: int = PrivateAttr(default=0)
    _calls: list[Any] = PrivateAttr(default_factory=list)

    async def generate_content_async(
        self, llm_request: Any, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self._calls.append(llm_request)
        # Clamp rather than raise once exhausted, so a test that runs the
        # same scripted agent tree more than once (e.g. to prove
        # redelivery is a no-op) doesn't need to pad the script with
        # duplicate trailing responses.
        response = self.responses[min(self._index, len(self.responses) - 1)]
        self._index += 1
        yield response

    @property
    def calls(self) -> list[Any]:
        return self._calls


def tool_call_response(name: str, args: dict) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
        )
    )


def transfer_response(agent_name: str) -> LlmResponse:
    return tool_call_response("transfer_to_agent", {"agent_name": agent_name})


def text_then_transfer_response(text: str, agent_name: str) -> LlmResponse:
    """Text plus a transfer call in the same turn.

    A sub-agent that only returns plain text ends the invocation there - ADK
    does not ask it again. To hand off *and* say something (e.g. the
    researcher's characterization, followed by transferring to the
    reporter), both parts must be in one scripted response.
    """
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(text=text),
                types.Part(
                    function_call=types.FunctionCall(
                        name="transfer_to_agent", args={"agent_name": agent_name}
                    )
                ),
            ],
        )
    )


def text_response(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def function_responses_in(llm_request: Any) -> dict[str, Any]:
    """Every function_response payload seen in a captured LlmRequest's history.

    Proves a tool actually executed (not just that a call to it was
    scripted) by inspecting the response ADK fed back to the model.
    """
    found: dict[str, Any] = {}
    for content in llm_request.contents:
        for part in content.parts or []:
            if part.function_response is not None:
                found[part.function_response.name] = part.function_response.response
    return found


def build_scripted_agent_tree(fake: FakeLlm) -> Agent:
    """A triage/researcher/reporter tree wired to ``fake`` instead of a real model.

    Uses the real tool functions from ``oncall_triage.tools`` - callers are
    expected to have already pointed them at test stores via
    ``oncall_triage.tools.configure()``.
    """
    researcher = Agent(
        name="researcher",
        model=fake,
        description="Investigates a new error and characterizes it.",
        instruction="You are the researcher.",
    )
    reporter = Agent(
        name="reporter",
        model=fake,
        description="Formats the final report shown to the oncall engineer.",
        instruction="You are the reporter.",
    )
    triage = Agent(
        name="triage",
        model=fake,
        description="Routes an alert to researcher or reporter.",
        instruction="You are the triage agent.",
        tools=[get_alert, get_recent_alerts, check_known, remember_issue],
        sub_agents=[researcher, reporter],
    )
    return triage
