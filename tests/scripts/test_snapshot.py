"""The recorded view visitors see without a token comes from the two console reads (#131)."""

import json

import pytest

from scripts import snapshot


def _fake_http(responses):
    def http(method, url, headers=None, body=None):
        assert method == "GET"
        assert headers == {"Authorization": "Bearer t"}
        path = url.removeprefix("https://api")
        status, payload = responses[path]
        return status, json.dumps(payload).encode()

    return http


def test_snapshot_holds_alerts_known_issues_and_provenance(monkeypatch):
    monkeypatch.setattr(
        snapshot,
        "http",
        _fake_http(
            {
                "/alerts?limit=50": (200, [{"alert_id": "A", "verdict": {"action": "ack"}}]),
                "/known-issues": (200, [{"service": "payments", "pattern": "pool"}]),
            }
        ),
    )
    result = snapshot.build_snapshot("https://api", "t", run_url="https://gh/run/1")
    assert result["alerts"] == [{"alert_id": "A", "verdict": {"action": "ack"}}]
    assert result["known_issues"] == [{"service": "payments", "pattern": "pool"}]
    assert result["run_url"] == "https://gh/run/1"
    assert result["recorded_at"].endswith("Z")


def test_a_failed_read_is_an_error_not_an_empty_snapshot(monkeypatch):
    monkeypatch.setattr(
        snapshot,
        "http",
        _fake_http({"/alerts?limit=50": (500, {"error": "boom"}), "/known-issues": (200, [])}),
    )
    with pytest.raises(snapshot.SmokeError, match="snapshot-alerts"):
        snapshot.build_snapshot("https://api", "t")


def test_estate_alerts_come_first_and_smoke_probes_are_capped():
    def alert(name, i):
        return {"alert_id": f"{name}-{i}", "alert_name": name}

    newest_first = (
        [alert("SmokeTest", i) for i in range(3)]
        + [alert("SmokeTestKnownIssue", i) for i in range(3)]
        + [alert("PoolExhausted", 0), alert("KafkaConsumerLag", 0)]
    )
    ordered = snapshot.order_for_visitors(newest_first)
    assert [a["alert_id"] for a in ordered[:2]] == ["PoolExhausted-0", "KafkaConsumerLag-0"]
    assert len(ordered) == 2 + snapshot._SMOKE_KEEP
    assert all(snapshot.is_smoke(a) for a in ordered[2:])
    assert ordered[2]["alert_id"] == "SmokeTest-0"


def test_run_url_only_inside_actions():
    env = {"GITHUB_RUN_ID": "7", "GITHUB_REPOSITORY": "o/r", "GITHUB_SERVER_URL": "https://gh"}
    assert snapshot.run_url_from_env(env) == "https://gh/o/r/actions/runs/7"
    assert snapshot.run_url_from_env({}) == ""
