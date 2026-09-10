from __future__ import annotations

from bank.azure._shared.hmac_sign import sign as azure_sign
from bank.k8s._shared.hmac_sign import sign, signed_headers
from services.ingest.hmac_auth import sign as ingest_sign
from services.ingest.hmac_auth import verify

SECRET = b"test-secret"


def test_sign_matches_the_ingest_algorithm():
    timestamp = "1700000000"
    body = b'{"hello": "world"}'

    assert sign(SECRET, timestamp, body) == ingest_sign(SECRET, timestamp, body)


def test_sign_matches_the_azure_copy():
    timestamp = "1700000000"
    body = b'{"hello": "world"}'

    assert sign(SECRET, timestamp, body) == azure_sign(SECRET, timestamp, body)


def test_signed_headers_are_accepted_by_ingest_verify():
    body = b'{"a": 1}'

    headers = signed_headers(SECRET, body, now=lambda: 1700000000.0)

    assert headers["Content-Type"] == "application/json"
    verify(
        SECRET,
        headers["X-Nordwind-Timestamp"],
        body,
        headers["X-Nordwind-Signature"],
        now=1700000000.0,
    )
