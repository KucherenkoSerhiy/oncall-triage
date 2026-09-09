import pytest

from services.ingest.canonical import CanonicalAlert
from services.ingest.scrub import scrub_alert, scrub_text

CORPUS = [
    ("4111 1111 1111 1111", "[REDACTED:PAN]"),  # Visa test number, spaced
    ("5555-5555-5555-4444", "[REDACTED:PAN]"),  # Mastercard test number, dashed
    ("3782 822463 10005", "[REDACTED:PAN]"),  # Amex test number, spaced
    ("1234567890123", "1234567890123"),  # 13 digits, fails Luhn: must survive
    ("DE89370400440532013000", "[REDACTED:IBAN]"),
    ("GB29NWBK60161331926819", "[REDACTED:IBAN]"),
    ("alice@example.com", "[REDACTED:EMAIL]"),
    ("bob.smith@my-bank.co.uk", "[REDACTED:EMAIL]"),
]


@pytest.mark.parametrize("text,expected", CORPUS)
def test_scrub_text_corpus(text, expected):
    assert scrub_text(text) == expected


def test_scrub_text_mixed_line():
    line = (
        "User bob@example.com attempted payment with card 4111 1111 1111 1111 "
        "from IBAN DE89370400440532013000"
    )
    result = scrub_text(line)
    assert "[REDACTED:EMAIL]" in result
    assert "[REDACTED:PAN]" in result
    assert "[REDACTED:IBAN]" in result
    assert "bob@example.com" not in result
    assert "4111" not in result
    assert "DE89370400440532013000" not in result


def _make_alert(**overrides) -> CanonicalAlert:
    fields = dict(
        alert_id="A" * 26,
        fingerprint="f",
        source="bankops",
        estate="aws",
        service="svc",
        alert_name="name",
        severity="sev1",
        title="Card 4111 1111 1111 1111 charged",
        description="Contact bob@example.com for details",
        sample_logs=("card 5555-5555-5555-4444 declined",),
        labels={"contact": "alice@example.com"},
        fired_at="2024-01-01T00:00:00Z",
        received_at="2024-01-01T00:00:01Z",
        raw={},
    )
    fields.update(overrides)
    return CanonicalAlert(**fields)


def test_scrub_alert_scrubs_top_level_fields():
    alert = _make_alert()
    scrubbed = scrub_alert(alert)
    assert scrubbed.title == "Card [REDACTED:PAN] charged"
    assert scrubbed.description == "Contact [REDACTED:EMAIL] for details"
    assert scrubbed.sample_logs == ("card [REDACTED:PAN] declined",)
    assert scrubbed.labels["contact"] == "[REDACTED:EMAIL]"


def test_scrub_alert_scrubs_raw_recursively():
    alert = _make_alert(
        raw={
            "nested": {"note": "iban DE89370400440532013000"},
            "list": ["email carol@example.com", "safe text", 42],
        }
    )
    scrubbed = scrub_alert(alert)
    assert "[REDACTED:IBAN]" in scrubbed.raw["nested"]["note"]
    assert "[REDACTED:EMAIL]" in scrubbed.raw["list"][0]
    assert scrubbed.raw["list"][1] == "safe text"
    assert scrubbed.raw["list"][2] == 42
