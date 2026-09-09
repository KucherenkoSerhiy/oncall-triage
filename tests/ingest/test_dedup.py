from datetime import UTC, datetime, timedelta

import boto3

from services.ingest.canonical import CanonicalAlert
from services.ingest.dedup import AlertStore

T0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _alert(alert_id: str, received_at: str, fingerprint: str = "fp-1") -> CanonicalAlert:
    return CanonicalAlert(
        alert_id=alert_id,
        fingerprint=fingerprint,
        source="bankops",
        estate="aws",
        service="svc",
        alert_name="HighLatency",
        severity="sev2",
        title="High latency",
        description="",
        sample_logs=(),
        labels={},
        fired_at=received_at,
        received_at=received_at,
        raw={},
    )


def test_put_new_writes_queued_with_one_occurrence(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    alert = _alert("A" * 26, _iso(T0))
    store.put_new(alert)

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    item = table.get_item(Key={"alert_id": alert.alert_id})["Item"]
    assert item["status"] == "queued"
    assert item["occurrences"] == 1


def test_find_open_returns_none_when_nothing_stored(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    assert store.find_open("no-such-fingerprint", _iso(T0)) is None


def test_find_open_finds_recent_queued_alert(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    alert = _alert("A" * 26, _iso(T0))
    store.put_new(alert)

    found = store.find_open("fp-1", _iso(T0 + timedelta(minutes=5)))
    assert found is not None
    assert found["alert_id"] == alert.alert_id


def test_find_open_respects_thirty_minute_window(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    alert = _alert("A" * 26, _iso(T0))
    store.put_new(alert)

    assert store.find_open("fp-1", _iso(T0 + timedelta(minutes=31))) is None


def test_find_open_matches_triaged_status(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    alert = _alert("A" * 26, _iso(T0))
    store.put_new(alert)

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    table.update_item(
        Key={"alert_id": alert.alert_id},
        UpdateExpression="SET #status = :s",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":s": "triaged"},
    )

    found = store.find_open("fp-1", _iso(T0 + timedelta(minutes=5)))
    assert found is not None


def test_find_open_ignores_closed_status(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    alert = _alert("A" * 26, _iso(T0))
    store.put_new(alert)

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    table.update_item(
        Key={"alert_id": alert.alert_id},
        UpdateExpression="SET #status = :s",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":s": "closed"},
    )

    assert store.find_open("fp-1", _iso(T0 + timedelta(minutes=5))) is None


def test_bump_increments_occurrences_and_sets_last_seen(moto_infra):
    store = AlertStore(moto_infra["table_name"])
    alert = _alert("A" * 26, _iso(T0))
    store.put_new(alert)

    bump_time = _iso(T0 + timedelta(minutes=5))
    store.bump(alert.alert_id, bump_time)

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    item = table.get_item(Key={"alert_id": alert.alert_id})["Item"]
    assert item["occurrences"] == 2
    assert item["last_seen_at"] == bump_time
