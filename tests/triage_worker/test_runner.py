from __future__ import annotations

import pytest

from oncall_triage import tools
from oncall_triage.stores import AlertRepo, InMemoryAlertsTable, JsonFileStore
from services.triage_worker.runner import TriageRunner
from tests.triage_worker.fake_llm import (
    FakeLlm,
    build_scripted_agent_tree,
    function_responses_in,
    text_response,
    text_then_transfer_response,
    tool_call_response,
    transfer_response,
)


@pytest.fixture(autouse=True)
def configured_stores(tmp_path):
    known_path = tmp_path / "known_issues.json"
    known_store = JsonFileStore(known_path)
    known_store.add_known(
        "*", "connection pool exhausted", "Known scaling limit.", taught_by="seed"
    )

    table = InMemoryAlertsTable()
    table.put_item(
        Item={
            "alert_id": "A1",
            "service": "payments-service",
            "alert_name": "HighLatency",
            "severity": "sev2",
            "status": "queued",
            "received_at": "2026-09-09T10:00:00Z",
            "title": "connection pool exhausted during checkout",
        }
    )
    table.put_item(
        Item={
            "alert_id": "A2",
            "service": "inventory-service",
            "alert_name": "SyncTimeout",
            "severity": "sev1",
            "status": "queued",
            "received_at": "2026-09-09T10:00:00Z",
            "title": "StockReconciliationTimeout waiting on warehouse-sync-3",
        }
    )
    tools.configure(known_store, AlertRepo(table))
    yield
    tools.configure(JsonFileStore(), AlertRepo())


def test_known_alert_produces_format_a_and_calls_tools():
    fake = FakeLlm(
        responses=[
            tool_call_response("get_alert", {"alert_id": "A1"}),
            tool_call_response(
                "check_known",
                {
                    "service": "payments-service",
                    "error_text": "connection pool exhausted during checkout",
                },
            ),
            transfer_response("reporter"),
            text_response(
                "Known issue: connection pool exhausted - Known scaling limit.\n"
                "```verdict\n"
                '{"known": true, "severity": "sev2", "action": "ack", '
                '"summary": "Known scaling limit"}\n'
                "```"
            ),
        ]
    )
    tree = build_scripted_agent_tree(fake)
    runner = TriageRunner(agent_factory=lambda: tree)

    result = runner.run(
        {"alert_id": "A1", "title": "connection pool exhausted during checkout", "severity": "sev2"}
    )

    assert "Known issue" in result.text
    assert result.verdict == {
        "known": True,
        "severity": "sev2",
        "action": "ack",
        "summary": "Known scaling limit",
    }
    assert result.verdict_parse_error is False
    assert result.model == "fake-1"

    tool_responses = function_responses_in(fake.calls[2])
    assert tool_responses["get_alert"]["alert_id"] == "A1"
    assert tool_responses["check_known"]["known"] is True


def test_new_alert_produces_format_b_with_verdict_block():
    fake = FakeLlm(
        responses=[
            tool_call_response("get_alert", {"alert_id": "A2"}),
            tool_call_response(
                "check_known",
                {"service": "inventory-service", "error_text": "StockReconciliationTimeout"},
            ),
            transfer_response("researcher"),
            text_then_transfer_response(
                "Cause: downstream dependency failure. Severity: medium. "
                "Next step: check warehouse-sync-3.",
                "reporter",
            ),
            text_response(
                "Error: StockReconciliationTimeout\n"
                "Characterization: downstream dependency failure, medium severity\n"
                "Recommendation: monitor for now\n"
                "```verdict\n"
                '{"known": false, "severity": "sev1", "action": "page", '
                '"summary": "New sync timeout"}\n'
                "```"
            ),
        ]
    )
    tree = build_scripted_agent_tree(fake)
    runner = TriageRunner(agent_factory=lambda: tree)

    result = runner.run(
        {"alert_id": "A2", "title": "StockReconciliationTimeout", "severity": "sev1"}
    )

    assert "Recommendation" in result.text
    assert result.verdict["known"] is False
    assert result.verdict["action"] == "page"
    assert result.verdict_parse_error is False

    tool_responses = function_responses_in(fake.calls[1])
    assert tool_responses["get_alert"]["alert_id"] == "A2"


def test_missing_verdict_block_falls_back_and_flags_parse_error():
    fake = FakeLlm(responses=[text_response("Some free-form text with no verdict block at all.")])
    tree = build_scripted_agent_tree(fake)
    runner = TriageRunner(agent_factory=lambda: tree)

    result = runner.run({"alert_id": "A3", "title": "whatever", "severity": "sev3"})

    assert result.verdict_parse_error is True
    assert result.verdict["known"] is False
    assert result.verdict["severity"] == "sev3"
    assert result.verdict["action"] == "monitor"
    assert result.verdict["summary"] == "Some free-form text with no verdict block at all."


def test_malformed_verdict_json_falls_back_and_flags_parse_error():
    fake = FakeLlm(responses=[text_response("Report text.\n```verdict\nnot valid json\n```")])
    tree = build_scripted_agent_tree(fake)
    runner = TriageRunner(agent_factory=lambda: tree)

    result = runner.run({"alert_id": "A4", "title": "whatever", "severity": "sev4"})

    assert result.verdict_parse_error is True
    assert result.verdict["severity"] == "sev4"


def test_prompt_hash_is_stable_sha256_of_instructions():
    fake = FakeLlm(
        responses=[
            text_response(
                '```verdict\n{"known": false, "severity": "sev3", '
                '"action": "monitor", "summary": "x"}\n```'
            )
        ]
    )
    tree = build_scripted_agent_tree(fake)
    runner = TriageRunner(agent_factory=lambda: tree)

    result = runner.run({"alert_id": "A5", "title": "whatever", "severity": "sev3"})

    import hashlib

    expected = hashlib.sha256(
        ("You are the triage agent." + "You are the researcher." + "You are the reporter.").encode()
    ).hexdigest()
    assert result.prompt_hash == expected
