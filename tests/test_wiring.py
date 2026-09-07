"""Structural/wiring tests: no live model call, no API key required."""

import json

import pytest


def test_no_api_key_needed_for_import(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
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


def test_all_three_tools_attached_to_triage():
    from oncall_triage.agent import root_agent

    tool_names = {t.__name__ for t in root_agent.tools}
    assert tool_names == {"get_logs", "check_known", "remember_issue"}


def test_researcher_and_reporter_have_descriptions():
    from oncall_triage.agent import reporter, researcher

    assert researcher.description and len(researcher.description) > 10
    assert reporter.description and len(reporter.description) > 10


def test_get_logs_known_service_returns_errors():
    from oncall_triage.tools import get_logs

    logs = get_logs("payments-service")
    assert isinstance(logs, list)
    assert len(logs) >= 2


def test_get_logs_unknown_service_is_safe():
    from oncall_triage.tools import get_logs

    logs = get_logs("nonexistent-service")
    assert isinstance(logs, list)
    assert len(logs) == 1
    assert "nonexistent-service" in logs[0]


def test_get_logs_covers_at_least_three_services():
    from oncall_triage.tools import _MOCK_LOGS

    assert len(_MOCK_LOGS) >= 3
    for _service, lines in _MOCK_LOGS.items():
        assert len(lines) >= 1


@pytest.fixture
def temp_store(tmp_path, monkeypatch):
    store_path = tmp_path / "known_issues.json"
    seed = {
        "issues": [{"pattern": "connection pool exhausted", "explanation": "Known scaling limit."}]
    }
    store_path.write_text(json.dumps(seed), encoding="utf-8")
    monkeypatch.setenv("TRIAGE_STORE_PATH", str(store_path))
    return store_path


def test_check_known_hit(temp_store):
    from oncall_triage.tools import check_known

    result = check_known("ERROR connection pool exhausted while doing X")
    assert result["known"] is True
    assert result["pattern"] == "connection pool exhausted"
    assert "scaling limit" in result["explanation"].lower()


def test_check_known_miss(temp_store):
    from oncall_triage.tools import check_known

    result = check_known("ERROR totally novel thing happened")
    assert result["known"] is False
    assert result["explanation"] is None


def test_remember_issue_persists_and_is_found(temp_store):
    from oncall_triage.tools import check_known, remember_issue

    result = remember_issue(
        "NullPointerException in RefundCalculator", "Known null-safety bug, fix scheduled."
    )
    assert result["stored"] is True

    found = check_known("ERROR NullPointerException in RefundCalculator.applyDiscount")
    assert found["known"] is True
    assert found["pattern"] == "NullPointerException in RefundCalculator"

    on_disk = json.loads(temp_store.read_text(encoding="utf-8"))
    patterns = [i["pattern"] for i in on_disk["issues"]]
    assert "NullPointerException in RefundCalculator" in patterns


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


def test_store_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    from oncall_triage import store

    path = tmp_path / "issues.json"
    store.add_known("disk full", "log rotation misconfigured", path=path)
    store.add_known("cache stampede", "expected during deploys", path=path)

    assert not list(tmp_path.glob("*.tmp")), "temp file must be replaced, not left"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert [i["pattern"] for i in data["issues"]] == ["disk full", "cache stampede"]
    assert store.find_known("ERROR: disk FULL on /var", path=path) is not None
