from __future__ import annotations

from datetime import UTC, datetime, timedelta

import boto3

from bank.ops.slo_reporter import handler


class _FakeCloudWatch:
    def __init__(self):
        self.calls = []

    def put_metric_data(self, **kwargs):
        self.calls.append(kwargs)


def _alerts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )


def _verdicts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["verdicts_table"]
    )


def _yesterday_iso(hour: int, minute: int = 0) -> str:
    today = datetime.now(UTC)
    yesterday = datetime(today.year, today.month, today.day, tzinfo=UTC) - timedelta(days=1)
    return yesterday.replace(hour=hour, minute=minute).isoformat().replace("+00:00", "Z")


def _put_alert(moto_infra, alert_id: str, received_at: str) -> None:
    _alerts_table(moto_infra).put_item(
        Item={"alert_id": alert_id, "status": "triaged", "received_at": received_at}
    )


def _put_verdict(moto_infra, alert_id: str, created_at: str, model: str = "claude") -> None:
    _verdicts_table(moto_infra).put_item(
        Item={"alert_id": alert_id, "created_at": created_at, "model": model}
    )


def _run(moto_infra, monkeypatch) -> tuple[dict, _FakeCloudWatch]:
    fake_cloudwatch = _FakeCloudWatch()
    monkeypatch.setattr(handler, "_cloudwatch_client", lambda: fake_cloudwatch)
    result = handler.lambda_handler({}, None)
    return result, fake_cloudwatch


def _metric_values(fake_cloudwatch: _FakeCloudWatch) -> dict:
    [call] = fake_cloudwatch.calls
    assert call["Namespace"] == "Nordwind/Triage"
    for metric in call["MetricData"]:
        assert metric["Dimensions"] == [{"Name": "estate", "Value": "all"}]
    return {m["MetricName"]: m["Value"] for m in call["MetricData"]}


def test_two_alerts_with_verdicts_p95_attainment_count(moto_infra, monkeypatch):
    _put_alert(moto_infra, "A" * 26, _yesterday_iso(10, 0))
    _put_verdict(moto_infra, "A" * 26, _yesterday_iso(10, 1))  # latency 60s -> within SLO

    _put_alert(moto_infra, "B" * 26, _yesterday_iso(11, 0))
    _put_verdict(moto_infra, "B" * 26, _yesterday_iso(11, 7))  # latency 420s -> misses SLO

    result, fake_cloudwatch = _run(moto_infra, monkeypatch)

    assert result == {"alerts": 2, "p95_seconds": 420, "attainment": 0.5}

    values = _metric_values(fake_cloudwatch)
    assert values["AlertsTriaged"] == 2
    assert values["VerdictLatencyP95"] == 420
    assert values["SloAttainment"] == 0.5


def test_alert_without_verdict_is_ignored(moto_infra, monkeypatch):
    _put_alert(moto_infra, "C" * 26, _yesterday_iso(9, 0))
    # no verdict written for this alert

    result, fake_cloudwatch = _run(moto_infra, monkeypatch)

    assert result == {"alerts": 0, "p95_seconds": None, "attainment": None}
    values = _metric_values(fake_cloudwatch)
    assert values == {"AlertsTriaged": 0}


def test_cap_short_circuit_counts_as_a_miss_but_still_feeds_p95(moto_infra, monkeypatch):
    _put_alert(moto_infra, "D" * 26, _yesterday_iso(8, 0))
    _put_verdict(moto_infra, "D" * 26, _yesterday_iso(8, 0), model="cap")

    result, _fake_cloudwatch = _run(moto_infra, monkeypatch)

    assert result["alerts"] == 1
    assert result["p95_seconds"] == 0
    assert result["attainment"] == 0.0


def test_empty_day_publishes_zero_count_and_no_p95(moto_infra, monkeypatch):
    result, fake_cloudwatch = _run(moto_infra, monkeypatch)

    assert result == {"alerts": 0, "p95_seconds": None, "attainment": None}
    values = _metric_values(fake_cloudwatch)
    assert values == {"AlertsTriaged": 0}
    assert "VerdictLatencyP95" not in values
    assert "SloAttainment" not in values
