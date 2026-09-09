from __future__ import annotations

import json

import boto3

from oncall_triage.stores import AlertRepo, DynamoStore, InMemoryAlertsTable, JsonFileStore


def test_json_file_store_wildcard_service_matches_any_service(tmp_path):
    path = tmp_path / "known_issues.json"
    path.write_text(
        json.dumps(
            {"issues": [{"service": "*", "pattern": "disk full", "explanation": "rotate logs"}]}
        ),
        encoding="utf-8",
    )
    store = JsonFileStore(path)

    assert store.find_known("payments-service", "ERROR disk full on /var") is not None
    assert store.find_known("inventory-service", "ERROR disk full on /var") is not None


def test_json_file_store_scopes_matches_to_service(tmp_path):
    path = tmp_path / "known_issues.json"
    path.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "service": "payments-service",
                        "pattern": "refund timeout",
                        "explanation": "known payments quirk",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    store = JsonFileStore(path)

    assert store.find_known("payments-service", "ERROR refund timeout") is not None
    assert store.find_known("inventory-service", "ERROR refund timeout") is None


def test_json_file_store_add_known_then_list_known(tmp_path):
    path = tmp_path / "known_issues.json"
    store = JsonFileStore(path)

    store.add_known("payments-service", "refund timeout", "known payments quirk", taught_by="alice")
    store.add_known("*", "disk full", "rotate logs", taught_by="bob")

    payments_issues = store.list_known("payments-service")
    assert len(payments_issues) == 1
    assert payments_issues[0]["pattern"] == "refund timeout"
    assert payments_issues[0]["taught_by"] == "alice"


def test_dynamo_store_find_known_matches_service_and_wildcard(moto_infra):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["known_issues_table"]
    )
    store = DynamoStore(table)
    store.add_known("payments-service", "refund timeout", "known payments quirk", taught_by="alice")
    store.add_known("*", "connection pool exhausted", "known scaling limit", taught_by="seed")

    scoped = store.find_known("payments-service", "ERROR refund timeout while processing")
    assert scoped is not None
    assert scoped["pattern"] == "refund timeout"

    wildcard = store.find_known("payments-service", "ERROR connection pool exhausted")
    assert wildcard is not None
    assert wildcard["pattern"] == "connection pool exhausted"

    other_service_only_scoped_miss = store.find_known("inventory-service", "ERROR refund timeout")
    assert other_service_only_scoped_miss is None


def test_dynamo_store_list_known_scopes_to_service(moto_infra):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["known_issues_table"]
    )
    store = DynamoStore(table)
    store.add_known("payments-service", "refund timeout", "known payments quirk", taught_by="alice")
    store.add_known("inventory-service", "sync timeout", "known inventory quirk", taught_by="bob")

    assert [i["pattern"] for i in store.list_known("payments-service")] == ["refund timeout"]


def test_alert_repo_get_alert_strips_raw(moto_infra):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )
    table.put_item(
        Item={
            "alert_id": "A1",
            "status": "queued",
            "received_at": "2026-09-09T10:00:00Z",
            "service": "payments-service",
            "alert_name": "HighLatency",
            "severity": "sev2",
            "title": "t",
            "occurrences": 3,
            "raw": {"webhook": "payload"},
        }
    )
    repo = AlertRepo(table)

    alert = repo.get_alert("A1")
    assert alert is not None
    assert alert["occurrences"] == 3
    assert "raw" not in alert


def test_alert_repo_get_alert_missing_returns_none(moto_infra):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )
    repo = AlertRepo(table)

    assert repo.get_alert("nonexistent") is None


def test_alert_repo_recent_alerts_filters_by_service_and_status(moto_infra):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )
    repo = AlertRepo(table)

    def put(alert_id, service, status, received_at):
        table.put_item(
            Item={
                "alert_id": alert_id,
                "status": status,
                "received_at": received_at,
                "service": service,
                "alert_name": "HighLatency",
                "severity": "sev2",
                "title": "t",
            }
        )

    put("A1", "payments-service", "queued", "2026-09-09T10:00:00Z")
    put("A2", "payments-service", "triaged", "2026-09-09T10:05:00Z")
    put("A3", "payments-service", "resolved", "2026-09-09T10:06:00Z")
    put("A4", "inventory-service", "queued", "2026-09-09T10:07:00Z")

    results = repo.recent_alerts("payments-service", "2026-09-09T00:00:00Z")

    assert [item["alert_id"] for item in results] == ["A2", "A1"]


def test_in_memory_alerts_table_backs_alert_repo_without_aws():
    repo = AlertRepo(InMemoryAlertsTable())

    assert repo.get_alert("missing") is None
    assert repo.recent_alerts("some-service", "2026-01-01T00:00:00Z") == []
