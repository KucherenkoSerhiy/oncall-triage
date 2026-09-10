"""Verify DNSSEC and DNS resolution for the delegated zone (stdlib + `dig`).

Three checks against live DNS, each printed and none stopping the others:
1. `dig +dnssec triage.serhiykucherenko.dev NS` carries the `ad` flag and at
   least one RRSIG record (a validating resolver accepted the chain).
2. the DS record published at the parent (Cloudflare) names the same key
   tag as the RRSIG covering the zone's own DNSKEY set (independent of
   resolver validation - useful while caches are still catching up).
3. the console and API hostnames still resolve to something.

Run by `task dns-check` and, non-fatally, by the deploy workflow's smoke
job right after the DS record is first published - see infra/README.md
"DNSSEC" for why resolver caches make that window flaky rather than
broken. Skipped (exit 0) when `dig` is not on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable

_ZONE = "triage.serhiykucherenko.dev"
_HOSTNAMES = [_ZONE, "api.triage.serhiykucherenko.dev"]
_DIG_TIMEOUT_SECONDS = 10


def dig(*args: str, run=subprocess.run) -> str:
    result = run(
        ["dig", *args],
        capture_output=True,
        text=True,
        timeout=_DIG_TIMEOUT_SECONDS,
        check=False,
    )
    return result.stdout


def _flags(dig_output: str) -> list[str]:
    line = next((line for line in dig_output.splitlines() if line.startswith(";; flags:")), "")
    return line.split("flags:", 1)[1].split(";", 1)[0].split() if line else []


def check_ad_and_rrsig(zone: str = _ZONE) -> tuple[bool, str]:
    output = dig("+dnssec", zone, "NS")
    flags = _flags(output)
    if "ad" not in flags:
        return False, f"no `ad` flag in `dig +dnssec {zone} NS` (flags: {flags or 'none'})"
    if "RRSIG" not in output:
        return False, f"no RRSIG record in `dig +dnssec {zone} NS` response"
    return True, f"ad flag present, RRSIG returned for {zone}"


def _record_key_tags(dig_output: str, record_type: str) -> set[str]:
    tags = set()
    for line in dig_output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[2] != "IN":
            continue
        if record_type == "DS" and parts[3] == "DS":
            tags.add(parts[4])
        elif record_type == "DNSKEY" and parts[3] == "RRSIG" and parts[4] == "DNSKEY":
            tags.add(parts[10])
    return tags


def check_ds_matches_dnskey(zone: str = _ZONE) -> tuple[bool, str]:
    ds_tags = _record_key_tags(dig("DS", zone), "DS")
    if not ds_tags:
        return False, f"no DS record found for {zone} at the parent"
    dnskey_tags = _record_key_tags(dig("+dnssec", "DNSKEY", zone), "DNSKEY")
    if not dnskey_tags:
        return False, f"no signed DNSKEY set found for {zone}"
    if ds_tags.isdisjoint(dnskey_tags):
        return False, f"DS key tag(s) {ds_tags} match none of the DNSKEY key tag(s) {dnskey_tags}"
    return True, f"DS key tag(s) {ds_tags} match the zone's DNSKEY set"


def check_hostnames_resolve(hostnames: list[str] = _HOSTNAMES) -> tuple[bool, str]:
    unresolved = [host for host in hostnames if not dig("+short", host).strip()]
    if unresolved:
        return False, f"no answer for: {', '.join(unresolved)}"
    return True, f"resolved: {', '.join(hostnames)}"


def main() -> int:
    if shutil.which("dig") is None:
        print("SKIP: `dig` is not on PATH - install bind-utils/dnsutils to run this check")
        return 0

    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("ad flag + RRSIG", check_ad_and_rrsig),
        ("DS matches DNSKEY", check_ds_matches_dnskey),
        ("hostnames resolve", check_hostnames_resolve),
    ]

    all_ok = True
    for label, check in checks:
        try:
            ok, detail = check()
        except subprocess.TimeoutExpired:
            ok, detail = False, "`dig` timed out"
        print(f"{'OK' if ok else 'FAIL'}: {label} - {detail}")
        all_ok = all_ok and ok

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
