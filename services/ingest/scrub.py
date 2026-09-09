"""PII scrubbing: card numbers (Luhn-validated), IBANs and e-mail addresses."""

from __future__ import annotations

import re
from dataclasses import replace

from services.ingest.canonical import CanonicalAlert

_PAN_RE = re.compile(r"(?<!\d)(\d(?:[ -]?\d){12,18})(?!\d)")
_IBAN_RE = re.compile(r"\b([A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _redact_pan(match: re.Match[str]) -> str:
    candidate = match.group(1)
    digits = re.sub(r"[ -]", "", candidate)
    if _luhn_ok(digits):
        return "[REDACTED:PAN]"
    return candidate


def scrub_text(text: str) -> str:
    text = _PAN_RE.sub(_redact_pan, text)
    text = _IBAN_RE.sub("[REDACTED:IBAN]", text)
    text = _EMAIL_RE.sub("[REDACTED:EMAIL]", text)
    return text


def _scrub_value(value: object) -> object:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def _scrub_raw(raw: dict) -> dict:
    return {k: _scrub_value(v) for k, v in raw.items()}


def scrub_alert(alert: CanonicalAlert) -> CanonicalAlert:
    return replace(
        alert,
        title=scrub_text(alert.title),
        description=scrub_text(alert.description),
        sample_logs=tuple(scrub_text(line) for line in alert.sample_logs),
        labels={k: scrub_text(v) for k, v in alert.labels.items()},
        raw=_scrub_raw(alert.raw),
    )
