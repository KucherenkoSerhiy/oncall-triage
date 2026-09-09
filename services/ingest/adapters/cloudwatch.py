"""Adapter for SNS-delivered CloudWatch alarm state-change messages."""

from __future__ import annotations

import re

from services.ingest.adapters import NotAnAlert
from services.ingest.canonical import CanonicalAlert, compute_fingerprint, new_alert_id

_SERVICE_DIMENSION_NAMES = {"FunctionName", "QueueName", "TopicName"}
_DEMO_PREFIX = "nordwind-triage-demo-"


def _strip_prefix(value: str) -> str:
    return value[len(_DEMO_PREFIX) :] if value.startswith(_DEMO_PREFIX) else value


def _service_from_description(description: str) -> str | None:
    match = re.search(r"service=([^\s,;]+)", description)
    return match.group(1) if match else None


def _service_from_dimensions(dimensions: list[dict]) -> str | None:
    for dim in dimensions:
        if dim.get("name") in _SERVICE_DIMENSION_NAMES:
            return _strip_prefix(dim["value"])
    return None


def to_canonical(payload: dict, received_at: str) -> CanonicalAlert:
    new_state = payload.get("NewStateValue")
    if new_state != "ALARM":
        raise NotAnAlert(f"NewStateValue={new_state!r} is not ALARM")

    alarm_name = payload.get("AlarmName", "")
    alarm_description = payload.get("AlarmDescription") or ""
    reason = payload.get("NewStateReason", "")
    trigger = payload.get("Trigger", {})
    dimensions = trigger.get("Dimensions", [])

    service = (
        _service_from_description(alarm_description)
        or _service_from_dimensions(dimensions)
        or "unknown"
    )

    if "Sev1" in alarm_name:
        severity = "sev1"
    elif "Sev2" in alarm_name:
        severity = "sev2"
    else:
        severity = "sev3"

    labels = {dim["name"]: dim["value"] for dim in dimensions}
    fingerprint = compute_fingerprint("cloudwatch", service, alarm_name, labels)

    return CanonicalAlert(
        alert_id=new_alert_id(),
        fingerprint=fingerprint,
        source="cloudwatch",
        estate="aws",
        service=service,
        alert_name=alarm_name,
        severity=severity,
        title=f"{alarm_name}: {reason}",
        description=alarm_description,
        sample_logs=(),
        labels=labels,
        fired_at=payload.get("StateChangeTime", ""),
        received_at=received_at,
        raw=payload,
    )
