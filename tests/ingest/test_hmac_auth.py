import pytest

from services.ingest.hmac_auth import HmacError, sign, verify

SECRET = b"topsecret"


def test_sign_produces_sha256_prefixed_hex():
    sig = sign(SECRET, "1700000000", b'{"a":1}')
    assert sig.startswith("sha256=")
    assert len(sig) == len("sha256=") + 64


def test_verify_happy_path():
    ts = "1700000000"
    body = b'{"a":1}'
    sig = sign(SECRET, ts, body)
    verify(SECRET, ts, body, sig, now=1700000000)


def test_verify_rejects_skew_too_far_in_past():
    ts = "1700000000"
    body = b"{}"
    sig = sign(SECRET, ts, body)
    with pytest.raises(HmacError):
        verify(SECRET, ts, body, sig, now=1700000000 + 301)


def test_verify_rejects_skew_too_far_in_future():
    ts = "1700000000"
    body = b"{}"
    sig = sign(SECRET, ts, body)
    with pytest.raises(HmacError):
        verify(SECRET, ts, body, sig, now=1700000000 - 301)


def test_verify_accepts_skew_within_window():
    ts = "1700000000"
    body = b"{}"
    sig = sign(SECRET, ts, body)
    verify(SECRET, ts, body, sig, now=1700000000 + 299)
    verify(SECRET, ts, body, sig, now=1700000000 - 299)


def test_verify_rejects_bad_signature():
    with pytest.raises(HmacError):
        verify(SECRET, "1700000000", b"{}", "sha256=" + "0" * 64, now=1700000000)


def test_verify_rejects_missing_signature():
    with pytest.raises(HmacError):
        verify(SECRET, "1700000000", b"{}", "", now=1700000000)


def test_verify_rejects_malformed_signature_prefix():
    with pytest.raises(HmacError):
        verify(SECRET, "1700000000", b"{}", "deadbeef", now=1700000000)


def test_verify_rejects_malformed_timestamp():
    body = b"{}"
    sig = sign(SECRET, "not-a-number", body)
    with pytest.raises(HmacError):
        verify(SECRET, "not-a-number", body, sig, now=1700000000)
