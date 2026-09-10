"""Unit tests for scripts/dns_check.py (`dig` monkeypatched, no network)."""

from __future__ import annotations

from scripts import dns_check

_AD_FLAGS_WITH_RRSIG = (
    ";; flags: qr rd ra ad; QUERY: 1, ANSWER: 4, AUTHORITY: 0, ADDITIONAL: 1\n"
    "triage.serhiykucherenko.dev. 3600 IN NS ns-1.awsdns-01.com.\n"
    "triage.serhiykucherenko.dev. 3600 IN RRSIG NS 13 3 3600 20260201000000 "
    "20260101000000 12345 triage.serhiykucherenko.dev. abcdefsig==\n"
)

_DS_ANSWER = "triage.serhiykucherenko.dev. 3600 IN DS 12345 13 2 ABCDEF0123456789\n"

_DNSKEY_RRSIG = (
    "triage.serhiykucherenko.dev. 3600 IN DNSKEY 257 3 13 base64key==\n"
    "triage.serhiykucherenko.dev. 3600 IN RRSIG DNSKEY 13 3 3600 20260201000000 "
    "20260101000000 12345 triage.serhiykucherenko.dev. abcdefsig==\n"
)


def test_check_ad_and_rrsig_passes(monkeypatch):
    monkeypatch.setattr(dns_check, "dig", lambda *a: _AD_FLAGS_WITH_RRSIG)

    ok, detail = dns_check.check_ad_and_rrsig()

    assert ok
    assert "ad flag present" in detail


def test_check_ad_and_rrsig_fails_without_ad_flag(monkeypatch):
    no_ad = ";; flags: qr rd ra; QUERY: 1, ANSWER: 1\ntriage.dev. 3600 IN NS ns-1.\n"
    monkeypatch.setattr(dns_check, "dig", lambda *a: no_ad)

    ok, detail = dns_check.check_ad_and_rrsig()

    assert not ok
    assert "ad" in detail


def test_check_ad_and_rrsig_fails_without_rrsig(monkeypatch):
    no_rrsig = ";; flags: qr rd ra ad; QUERY: 1, ANSWER: 1\ntriage.dev. 3600 IN NS ns-1.\n"
    monkeypatch.setattr(dns_check, "dig", lambda *a: no_rrsig)

    ok, detail = dns_check.check_ad_and_rrsig()

    assert not ok
    assert "RRSIG" in detail


def test_check_ds_matches_dnskey_passes(monkeypatch):
    responses = iter([_DS_ANSWER, _DNSKEY_RRSIG])
    monkeypatch.setattr(dns_check, "dig", lambda *a: next(responses))

    ok, detail = dns_check.check_ds_matches_dnskey()

    assert ok
    assert "12345" in detail


def test_check_ds_matches_dnskey_fails_on_mismatch(monkeypatch):
    other_dnskey = _DNSKEY_RRSIG.replace("12345", "99999")
    responses = iter([_DS_ANSWER, other_dnskey])
    monkeypatch.setattr(dns_check, "dig", lambda *a: next(responses))

    ok, detail = dns_check.check_ds_matches_dnskey()

    assert not ok
    assert "match none" in detail


def test_check_ds_matches_dnskey_fails_when_no_ds_published(monkeypatch):
    responses = iter(["", _DNSKEY_RRSIG])
    monkeypatch.setattr(dns_check, "dig", lambda *a: next(responses))

    ok, detail = dns_check.check_ds_matches_dnskey()

    assert not ok
    assert "no DS record" in detail


def test_check_hostnames_resolve_passes(monkeypatch):
    monkeypatch.setattr(dns_check, "dig", lambda *a: "d111.cloudfront.net.\n")

    ok, detail = dns_check.check_hostnames_resolve(["triage.serhiykucherenko.dev"])

    assert ok
    assert "triage.serhiykucherenko.dev" in detail


def test_check_hostnames_resolve_fails_when_unresolved(monkeypatch):
    monkeypatch.setattr(dns_check, "dig", lambda *a: "")

    ok, detail = dns_check.check_hostnames_resolve(["triage.serhiykucherenko.dev"])

    assert not ok
    assert "triage.serhiykucherenko.dev" in detail


def test_main_skips_when_dig_missing(monkeypatch, capsys):
    monkeypatch.setattr(dns_check.shutil, "which", lambda _: None)

    exit_code = dns_check.main()

    assert exit_code == 0
    assert "SKIP" in capsys.readouterr().out


def test_main_returns_zero_when_all_checks_pass(monkeypatch, capsys):
    monkeypatch.setattr(dns_check.shutil, "which", lambda _: "/usr/bin/dig")
    monkeypatch.setattr(dns_check, "check_ad_and_rrsig", lambda: (True, "ok"))
    monkeypatch.setattr(dns_check, "check_ds_matches_dnskey", lambda: (True, "ok"))
    monkeypatch.setattr(dns_check, "check_hostnames_resolve", lambda: (True, "ok"))

    exit_code = dns_check.main()

    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_main_returns_one_when_a_check_fails(monkeypatch, capsys):
    monkeypatch.setattr(dns_check.shutil, "which", lambda _: "/usr/bin/dig")
    monkeypatch.setattr(dns_check, "check_ad_and_rrsig", lambda: (True, "ok"))
    monkeypatch.setattr(dns_check, "check_ds_matches_dnskey", lambda: (False, "mismatch"))
    monkeypatch.setattr(dns_check, "check_hostnames_resolve", lambda: (True, "ok"))

    exit_code = dns_check.main()

    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out
