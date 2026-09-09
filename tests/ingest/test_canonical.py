import time

import pytest

from services.ingest.canonical import CanonicalAlert, compute_fingerprint, new_alert_id


def _make(**overrides):
    fields = dict(
        alert_id="A" * 26,
        fingerprint="f",
        source="bankops",
        estate="aws",
        service="svc",
        alert_name="name",
        severity="sev1",
        title="title",
        description="",
        sample_logs=(),
        labels={},
        fired_at="2024-01-01T00:00:00Z",
        received_at="2024-01-01T00:00:00Z",
        raw={},
    )
    fields.update(overrides)
    return CanonicalAlert(**fields)


def test_unknown_source_raises_naming_field():
    with pytest.raises(ValueError, match="source"):
        _make(source="not-a-source")


def test_unknown_estate_raises_naming_field():
    with pytest.raises(ValueError, match="estate"):
        _make(estate="mars")


def test_unknown_severity_raises_naming_field():
    with pytest.raises(ValueError, match="severity"):
        _make(severity="sev9")


def test_empty_service_raises_naming_field():
    with pytest.raises(ValueError, match="service"):
        _make(service="")


def test_empty_alert_name_raises_naming_field():
    with pytest.raises(ValueError, match="alert_name"):
        _make(alert_name="")


def test_empty_title_raises_naming_field():
    with pytest.raises(ValueError, match="title"):
        _make(title="")


def test_fingerprint_is_stable_and_order_independent():
    a = compute_fingerprint("cloudwatch", "svc", "AlarmX", {"env": "prod", "region": "eu-north-1"})
    b = compute_fingerprint("cloudwatch", "svc", "AlarmX", {"region": "eu-north-1", "env": "prod"})
    assert a == b


def test_fingerprint_excludes_route_runbook_and_underscore_labels():
    base = compute_fingerprint("cloudwatch", "svc", "AlarmX", {"env": "prod"})
    with_extra = compute_fingerprint(
        "cloudwatch",
        "svc",
        "AlarmX",
        {"env": "prod", "route": "A", "runbook": "http://runbooks/x", "_internal": "y"},
    )
    assert base == with_extra


def test_fingerprint_changes_when_a_real_label_changes():
    a = compute_fingerprint("cloudwatch", "svc", "AlarmX", {"env": "prod"})
    b = compute_fingerprint("cloudwatch", "svc", "AlarmX", {"env": "staging"})
    assert a != b


def test_new_alert_id_is_26_chars():
    assert len(new_alert_id()) == 26


def test_new_alert_id_sorts_in_time_order():
    first = new_alert_id()
    time.sleep(0.002)
    second = new_alert_id()
    assert first < second


def test_to_item_from_item_roundtrip():
    alert = _make(sample_logs=("a", "b"), labels={"x": "y"})
    item = alert.to_item()
    assert item["sample_logs"] == ["a", "b"]
    assert item["labels"] == {"x": "y"}
    restored = CanonicalAlert.from_item(item)
    assert restored == alert
