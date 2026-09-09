"""Adapter for Prometheus Alertmanager webhooks."""

from __future__ import annotations

from services.ingest.adapters import NotAnAlert
from services.ingest.canonical import CanonicalAlert, compute_fingerprint, new_alert_id

_SEVERITY_MAP = {"critical": "sev1", "high": "sev2", "warning": "sev3"}


def _one_canonical(entry: dict, receiver: str, received_at: str) -> CanonicalAlert:
    labels = dict(entry.get("labels", {}))
    annotations = entry.get("annotations", {})

    service = labels.get("service") or labels.get("job") or "unknown"
    alert_name = labels.get("alertname", "")
    severity = _SEVERITY_MAP.get(labels.get("severity", ""), "sev4")
    title = annotations.get("summary") or alert_name
    description = annotations.get("description", "")

    labels["route"] = "A" if "kafka" in receiver else "B"
    fingerprint = compute_fingerprint("alertmanager", service, alert_name, labels)

    return CanonicalAlert(
        alert_id=new_alert_id(),
        fingerprint=fingerprint,
        source="alertmanager",
        estate="kubernetes",
        service=service,
        alert_name=alert_name,
        severity=severity,
        title=title,
        description=description,
        sample_logs=(),
        labels=labels,
        fired_at=entry.get("startsAt", ""),
        received_at=received_at,
        raw=entry,
    )


def to_canonical_many(payload: dict, received_at: str) -> list[CanonicalAlert]:
    receiver = payload.get("receiver", "")
    firing = [a for a in payload.get("alerts", []) if a.get("status") == "firing"]
    return [_one_canonical(entry, receiver, received_at) for entry in firing]


def to_canonical(payload: dict, received_at: str) -> CanonicalAlert:
    alerts = to_canonical_many(payload, received_at)
    if not alerts:
        raise NotAnAlert("no firing alerts in payload")
    return alerts[0]
