"""Adapter for the Azure Monitor common alert schema."""

from __future__ import annotations

import re

from services.ingest.adapters import NotAnAlert
from services.ingest.canonical import CanonicalAlert, compute_fingerprint, new_alert_id

_SEVERITY_MAP = {"Sev0": "sev1", "Sev1": "sev1", "Sev2": "sev2", "Sev3": "sev3", "Sev4": "sev4"}
_DEMO_PREFIX = "nordwind-triage-demo-"


def _service_from_target(target_id: str) -> str:
    segment = target_id.rstrip("/").rsplit("/", 1)[-1].lower()
    return segment[len(_DEMO_PREFIX) :] if segment.startswith(_DEMO_PREFIX) else segment


def to_canonical(payload: dict, received_at: str) -> CanonicalAlert:
    essentials = payload.get("data", {}).get("essentials", {})

    monitor_condition = essentials.get("monitorCondition")
    if monitor_condition != "Fired":
        raise NotAnAlert(f"monitorCondition={monitor_condition!r} is not Fired")

    alert_rule = essentials.get("alertRule", "")
    severity = _SEVERITY_MAP.get(essentials.get("severity", ""), "sev4")

    description = essentials.get("description", "")
    # The rule's description carries `service=<name>` (infra/azure/alerts.tf),
    # exactly like the CloudWatch alarms; the target resource is only a
    # fallback - on Azure it is the App Insights component or the workspace
    # ("appinsights", "logs"), never the bank service (#66).
    target_ids = essentials.get("alertTargetIDs", [])
    tagged = re.search(r"service=([^\s,;]+)", description)
    if tagged:
        service = tagged.group(1)
    elif target_ids:
        service = _service_from_target(target_ids[0])
    else:
        service = "unknown"

    labels: dict[str, str] = {}
    fingerprint = compute_fingerprint("azure-monitor", service, alert_rule, labels)

    return CanonicalAlert(
        alert_id=new_alert_id(),
        fingerprint=fingerprint,
        source="azure-monitor",
        estate="azure",
        service=service,
        alert_name=alert_rule,
        severity=severity,
        title=alert_rule,
        description=description,
        sample_logs=(),
        labels=labels,
        fired_at=essentials.get("firedDateTime", ""),
        received_at=received_at,
        raw=payload,
    )
