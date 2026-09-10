import copy
import json
from pathlib import Path

import pytest

from services.ingest.adapters import NotAnAlert, alertmanager, azure_monitor, bankops, cloudwatch

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


RECEIVED_AT = "2024-01-01T00:20:00Z"


def test_bankops_to_canonical():
    payload = _load("bankops")
    alert = bankops.to_canonical(payload, RECEIVED_AT)
    assert alert.source == "bankops"
    assert alert.estate == "aws"
    assert alert.service == "payments-api"
    assert alert.alert_name == "HighLatency"
    assert alert.severity == "sev2"
    assert alert.received_at == RECEIVED_AT
    assert len(alert.alert_id) == 26


def test_cloudwatch_alarm_to_canonical():
    payload = _load("cloudwatch")
    alert = cloudwatch.to_canonical(payload, RECEIVED_AT)
    assert alert.source == "cloudwatch"
    assert alert.estate == "aws"
    assert alert.service == "payments-worker"  # from AlarmDescription service=
    assert alert.severity == "sev2"  # AlarmName contains Sev2
    assert alert.alert_name == "nordwind-triage-demo-Sev2-QueueBacklog"
    assert "Threshold Crossed" in alert.title


def test_cloudwatch_service_falls_back_to_dimension_when_no_description_hint():
    payload = _load("cloudwatch")
    payload["AlarmDescription"] = "no service hint here"
    alert = cloudwatch.to_canonical(payload, RECEIVED_AT)
    assert alert.service == "payments-worker-queue"  # dimension value, demo prefix stripped


def test_cloudwatch_ok_state_raises_not_an_alert():
    payload = _load("cloudwatch")
    payload["NewStateValue"] = "OK"
    with pytest.raises(NotAnAlert):
        cloudwatch.to_canonical(payload, RECEIVED_AT)


def test_cloudwatch_insufficient_data_raises_not_an_alert():
    payload = _load("cloudwatch")
    payload["NewStateValue"] = "INSUFFICIENT_DATA"
    with pytest.raises(NotAnAlert):
        cloudwatch.to_canonical(payload, RECEIVED_AT)


def test_alertmanager_to_canonical_many_returns_only_firing():
    payload = _load("alertmanager")
    alerts = alertmanager.to_canonical_many(payload, RECEIVED_AT)
    assert len(alerts) == 2
    assert all(a.estate == "kubernetes" for a in alerts)
    first, second = alerts
    assert first.service == "ledger-consumer"  # label "service"
    assert first.severity == "sev1"  # critical
    assert first.title == "Kafka consumer lag is high"
    assert first.labels["route"] == "A"  # receiver contains "kafka"
    assert second.service == "ledger-consumer-job"  # falls back to "job"
    assert second.severity == "sev3"  # warning
    assert second.title == "KafkaConsumerLagHigh"  # no summary annotation


def test_alertmanager_to_canonical_returns_first_firing():
    payload = _load("alertmanager")
    alert = alertmanager.to_canonical(payload, RECEIVED_AT)
    assert alert.service == "ledger-consumer"


def test_alertmanager_to_canonical_raises_when_nothing_firing():
    payload = _load("alertmanager")
    payload["alerts"] = [a for a in payload["alerts"] if a["status"] != "firing"]
    with pytest.raises(NotAnAlert):
        alertmanager.to_canonical(payload, RECEIVED_AT)


def test_azure_monitor_fired_to_canonical():
    payload = _load("azure_monitor")
    alert = azure_monitor.to_canonical(payload, RECEIVED_AT)
    assert alert.source == "azure-monitor"
    assert alert.estate == "azure"
    assert alert.alert_name == "HighCpuAlert"
    assert alert.severity == "sev2"
    assert alert.service == "ledger-svc"  # last path segment, demo prefix stripped


def test_azure_monitor_resolved_raises_not_an_alert():
    payload = copy.deepcopy(_load("azure_monitor"))
    payload["data"]["essentials"]["monitorCondition"] = "Resolved"
    with pytest.raises(NotAnAlert):
        azure_monitor.to_canonical(payload, RECEIVED_AT)


@pytest.mark.parametrize(
    ("severity_label", "expected"),
    [("Sev0", "sev1"), ("Sev1", "sev1"), ("Sev2", "sev2"), ("Sev3", "sev3"), ("Sev4", "sev4")],
)
def test_azure_monitor_severity_mapping(severity_label, expected):
    payload = copy.deepcopy(_load("azure_monitor"))
    payload["data"]["essentials"]["severity"] = severity_label
    alert = azure_monitor.to_canonical(payload, RECEIVED_AT)
    assert alert.severity == expected


def test_azure_monitor_prefers_the_service_tag_in_the_description():
    # infra/azure/alerts.tf writes "service=<name>; ..." into every rule
    # description; the target resource is the App Insights component or the
    # workspace, not the bank service (#66).
    payload = _load("azure_monitor")
    essentials = payload["data"]["essentials"]
    essentials["description"] = "service=customer-notifications; provider returning 429."
    essentials["alertTargetIDs"] = [
        "/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/nordwind-triage-demo-appinsights"
    ]

    alert = azure_monitor.to_canonical(payload, "2026-09-10T01:00:00Z")

    assert alert.service == "customer-notifications"


def test_azure_monitor_falls_back_to_the_target_resource_without_a_tag():
    payload = _load("azure_monitor")
    alert = azure_monitor.to_canonical(payload, "2026-09-10T01:00:00Z")
    assert alert.service == "ledger-svc"
