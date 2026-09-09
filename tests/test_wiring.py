"""Structural/wiring tests: no live model call, no API key/network required."""

import json
from datetime import UTC, datetime

import pytest


def test_no_api_key_needed_for_import(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import importlib

    import oncall_triage.agent as agent_module

    importlib.reload(agent_module)
    assert agent_module.root_agent is not None


def test_root_agent_exists_and_importable():
    from oncall_triage import root_agent

    assert root_agent is not None
    assert root_agent.name == "triage"


def test_sub_agents_wiring_is_exactly_researcher_and_reporter():
    from oncall_triage.agent import reporter, researcher, root_agent

    names = [a.name for a in root_agent.sub_agents]
    assert names == ["researcher", "reporter"]
    assert root_agent.sub_agents[0] is researcher
    assert root_agent.sub_agents[1] is reporter


def test_all_four_tools_attached_to_triage():
    from oncall_triage.agent import root_agent

    tool_names = {t.__name__ for t in root_agent.tools}
    assert tool_names == {"get_alert", "get_recent_alerts", "check_known", "remember_issue"}


def test_researcher_and_reporter_have_descriptions():
    from oncall_triage.agent import reporter, researcher

    assert researcher.description and len(researcher.description) > 10
    assert reporter.description and len(reporter.description) > 10


@pytest.fixture
def configured_stores(tmp_path):
    from oncall_triage import tools
    from oncall_triage.stores import AlertRepo, InMemoryAlertsTable, JsonFileStore

    known_path = tmp_path / "known_issues.json"
    known_path.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "service": "*",
                        "pattern": "connection pool exhausted",
                        "explanation": "Known scaling limit.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    table = InMemoryAlertsTable()
    table.put_item(
        Item={
            "alert_id": "A1",
            "service": "payments-service",
            "alert_name": "HighLatency",
            "severity": "sev2",
            "status": "queued",
            "received_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "title": "High latency",
            "raw": {"webhook": "payload"},
        }
    )
    tools.configure(JsonFileStore(known_path), AlertRepo(table))
    yield table
    tools.configure(JsonFileStore(), AlertRepo())


def test_get_alert_returns_item_minus_raw(configured_stores):
    from oncall_triage.tools import get_alert

    alert = get_alert("A1")
    assert alert["alert_id"] == "A1"
    assert alert["service"] == "payments-service"
    assert "raw" not in alert


def test_get_alert_unknown_id_is_safe(configured_stores):
    from oncall_triage.tools import get_alert

    alert = get_alert("nonexistent")
    assert alert["found"] is False


def test_get_recent_alerts_returns_expected_shape(configured_stores):
    from oncall_triage.tools import get_recent_alerts

    alerts = get_recent_alerts("payments-service")
    assert len(alerts) == 1
    assert set(alerts[0]) == {"id", "alert_name", "severity", "received_at", "status"}
    assert alerts[0]["id"] == "A1"


def test_check_known_hit(configured_stores):
    from oncall_triage.tools import check_known

    result = check_known("payments-service", "ERROR connection pool exhausted while doing X")
    assert result["known"] is True
    assert result["pattern"] == "connection pool exhausted"
    assert "scaling limit" in result["explanation"].lower()


def test_check_known_miss(configured_stores):
    from oncall_triage.tools import check_known

    result = check_known("payments-service", "ERROR totally novel thing happened")
    assert result["known"] is False
    assert result["explanation"] is None


def test_remember_issue_persists_and_is_found(configured_stores):
    from oncall_triage.tools import check_known, remember_issue

    result = remember_issue(
        "payments-service",
        "NullPointerException in RefundCalculator",
        "Known null-safety bug, fix scheduled.",
    )
    assert result["stored"] is True

    found = check_known(
        "payments-service", "ERROR NullPointerException in RefundCalculator.applyDiscount"
    )
    assert found["known"] is True
    assert found["pattern"] == "NullPointerException in RefundCalculator"


def test_triage_instruction_mentions_both_handoff_conditions():
    from oncall_triage.agent import root_agent

    instruction = root_agent.instruction.lower()
    assert "researcher" in instruction
    assert "reporter" in instruction
    assert "known" in instruction
    assert "new" in instruction


def test_reporter_instruction_defines_both_formats():
    from oncall_triage.agent import reporter

    instruction = reporter.instruction.lower()
    assert "format a" in instruction
    assert "format b" in instruction
    assert "known" in instruction
    assert "new" in instruction


def test_reporter_instruction_requires_trailing_verdict_block():
    from oncall_triage.agent import reporter

    instruction = reporter.instruction.lower()
    assert "```verdict" in instruction
    assert '"action"' in instruction
    assert "page" in instruction and "monitor" in instruction and "ack" in instruction


def test_store_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    from oncall_triage.stores import JsonFileStore

    path = tmp_path / "issues.json"
    store = JsonFileStore(path)
    store.add_known(
        "payments-service", "disk full", "log rotation misconfigured", taught_by="tester"
    )
    store.add_known(
        "payments-service", "cache stampede", "expected during deploys", taught_by="tester"
    )

    assert not list(tmp_path.glob("*.tmp")), "temp file must be replaced, not left"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert [i["pattern"] for i in data["issues"]] == ["disk full", "cache stampede"]
    assert store.find_known("payments-service", "ERROR: disk FULL on /var") is not None


def test_build_model_defaults_to_anthropic_claude(monkeypatch):
    monkeypatch.delenv("TRIAGE_MODEL", raising=False)
    from google.adk.models.lite_llm import LiteLlm

    from oncall_triage.model import build_model

    model = build_model()
    assert isinstance(model, LiteLlm)
    assert model.model.startswith("anthropic/")


def test_build_model_honours_triage_model_env(monkeypatch):
    monkeypatch.setenv("TRIAGE_MODEL", "anthropic/claude-opus-4-6")
    from oncall_triage.model import build_model

    model = build_model()
    assert model.model == "anthropic/claude-opus-4-6"
