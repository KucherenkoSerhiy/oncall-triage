"""Canonical alert shape shared by every source adapter.

``CanonicalAlert`` is the single representation the rest of the ingest
pipeline (scrubber, dedup store, SQS payload) operates on. Adapters translate
a source-specific webhook/event payload into one (or more) of these.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

_SOURCES = {"cloudwatch", "azure-monitor", "alertmanager", "bankops"}
_ESTATES = {"aws", "azure", "kubernetes"}
_SEVERITIES = {"sev1", "sev2", "sev3", "sev4"}

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_EXCLUDED_FINGERPRINT_LABELS = {"route", "runbook"}


def new_alert_id() -> str:
    """A 26-character Crockford-base32 ULID: 48-bit ms timestamp + 80-bit randomness."""
    ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), "big")  # 80 bits
    value = (ms << 80) | randomness

    chars = []
    for _ in range(26):
        chars.append(_ULID_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def dynamodb_safe(value: Any) -> Any:
    """Return ``value`` with every float turned into a ``Decimal``.

    boto3's DynamoDB serializer refuses Python floats ("Float types are not
    supported. Use Decimal types instead"). Producer payloads kept under
    ``raw`` are arbitrary JSON - CloudWatch alarm messages carry
    ``Trigger.Threshold: 1.0`` and friends - and the first real alarm in M4
    crashed ingest on exactly that (#50). A JSON round-trip with
    ``parse_float=Decimal`` is the smallest faithful conversion; it also
    normalises tuples and other JSON-compatible containers to lists/dicts."""
    return json.loads(json.dumps(value), parse_float=Decimal)


def compute_fingerprint(source: str, service: str, alert_name: str, labels: dict[str, str]) -> str:
    """sha256 hex of ``source|service|alert_name|k1=v1,k2=v2,...`` (sorted, filtered labels)."""
    kept = {
        k: v
        for k, v in labels.items()
        if k not in _EXCLUDED_FINGERPRINT_LABELS and not k.startswith("_")
    }
    label_part = ",".join(f"{k}={v}" for k, v in sorted(kept.items()))
    payload = f"{source}|{service}|{alert_name}|{label_part}"
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class CanonicalAlert:
    alert_id: str
    fingerprint: str
    source: str
    estate: str
    service: str
    alert_name: str
    severity: str
    title: str
    description: str
    sample_logs: tuple[str, ...]
    labels: dict[str, str] = field(default_factory=dict)
    fired_at: str = ""
    received_at: str = ""
    raw: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source not in _SOURCES:
            raise ValueError(f"source: unknown source {self.source!r}")
        if self.estate not in _ESTATES:
            raise ValueError(f"estate: unknown estate {self.estate!r}")
        if self.severity not in _SEVERITIES:
            raise ValueError(f"severity: unknown severity {self.severity!r}")
        if not self.service:
            raise ValueError("service: must not be empty")
        if not self.alert_name:
            raise ValueError("alert_name: must not be empty")
        if not self.title:
            raise ValueError("title: must not be empty")

    def to_item(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "fingerprint": self.fingerprint,
            "source": self.source,
            "estate": self.estate,
            "service": self.service,
            "alert_name": self.alert_name,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "sample_logs": list(self.sample_logs),
            "labels": dict(self.labels),
            "fired_at": self.fired_at,
            "received_at": self.received_at,
            "raw": dynamodb_safe(self.raw),
        }

    @classmethod
    def from_item(cls, item: dict) -> CanonicalAlert:
        return cls(
            alert_id=item["alert_id"],
            fingerprint=item["fingerprint"],
            source=item["source"],
            estate=item["estate"],
            service=item["service"],
            alert_name=item["alert_name"],
            severity=item["severity"],
            title=item["title"],
            description=item["description"],
            sample_logs=tuple(item.get("sample_logs", [])),
            labels=dict(item.get("labels", {})),
            fired_at=item.get("fired_at", ""),
            received_at=item.get("received_at", ""),
            raw=item.get("raw", {}),
        )
