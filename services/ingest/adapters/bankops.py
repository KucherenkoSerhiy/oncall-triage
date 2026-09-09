"""Adapter for BankOps' own alerts: payload is already canonical-shaped.

Only ``alert_id``, ``fingerprint`` and ``received_at`` are missing and filled
in here; every other field is validated by ``CanonicalAlert.__post_init__``.
"""

from __future__ import annotations

from services.ingest.canonical import CanonicalAlert, compute_fingerprint, new_alert_id


def to_canonical(payload: dict, received_at: str) -> CanonicalAlert:
    source = payload.get("source", "")
    service = payload.get("service", "")
    alert_name = payload.get("alert_name", "")
    labels = dict(payload.get("labels", {}))
    fingerprint = compute_fingerprint(source, service, alert_name, labels)

    return CanonicalAlert(
        alert_id=new_alert_id(),
        fingerprint=fingerprint,
        source=source,
        estate=payload.get("estate", ""),
        service=service,
        alert_name=alert_name,
        severity=payload.get("severity", ""),
        title=payload.get("title", ""),
        description=payload.get("description", ""),
        sample_logs=tuple(payload.get("sample_logs", [])),
        labels=labels,
        fired_at=payload.get("fired_at", ""),
        received_at=received_at,
        raw=payload.get("raw", payload),
    )
