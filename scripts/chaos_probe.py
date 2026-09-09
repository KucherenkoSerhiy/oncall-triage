"""Live chaos probe for a bank estate (stdlib only, like scripts/smoke.py).

Sets a fault through the console API's chaos route, waits until the estate's
own monitoring turns it into an alert that reaches the triage spine, waits
for the verdict, prints it, and clears the fault. This is the milestone's
"live probe": the alert is produced by a real CloudWatch alarm (or Azure
Monitor rule, or Prometheus rule), not fired by hand.

    python scripts/chaos_probe.py --service payments --mode pool \
        --expect-alert PoolExhausted --expect-known

Run by the `smoke` job in `.github/workflows/deploy.yml` when the
`chaos_probe` dispatch input is set, and by hand with SMOKE_TOKEN exported.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.smoke import _DEFAULT_API_BASE, SmokeError, http, wait_for_verdict

# CloudWatch evaluates a 1-minute alarm within ~2 minutes of the metric
# arriving and the fault Lambda runs every minute, so 3-5 minutes is typical;
# Azure Monitor (M5) needs 5-7. Ten minutes covers both with margin.
_ALERT_TIMEOUT_SECONDS = 600
_ALERT_POLL_SECONDS = 15


def set_fault(api_base: str, token: str, service: str, mode: str, minutes: int) -> dict:
    body = json.dumps({"mode": mode, "minutes": minutes}).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    status, response = http("POST", f"{api_base}/chaos/{service}", headers=headers, body=body)
    if status != 201:
        raise SmokeError("set-fault", f"HTTP {status}: {response!r}")
    return json.loads(response)


def clear_fault(api_base: str, token: str, service: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    status, response = http("DELETE", f"{api_base}/chaos/{service}", headers=headers)
    if status not in (204, 404):
        raise SmokeError("clear-fault", f"HTTP {status}: {response!r}")


def wait_for_alert(
    api_base: str,
    token: str,
    service: str,
    alert_name_contains: str,
    not_before: str,
    timeout: float = _ALERT_TIMEOUT_SECONDS,
    interval: float = _ALERT_POLL_SECONDS,
    sleep=time.sleep,
    now=time.monotonic,
) -> dict:
    """Return the first alert for `service` whose name contains the marker and
    which was received after `not_before` (ISO timestamp) - older alerts from a
    previous probe must not satisfy a new one."""
    headers = {"Authorization": f"Bearer {token}"}
    deadline = now() + timeout
    while True:
        status, body = http("GET", f"{api_base}/alerts?limit=100", headers=headers)
        if status != 200:
            raise SmokeError("wait-for-alert", f"HTTP {status}: {body!r}")
        for alert in json.loads(body):
            if (
                alert.get("service") == service
                and alert_name_contains in (alert.get("alert_name") or "")
                and (alert.get("received_at") or "") >= not_before
            ):
                return alert
        if now() >= deadline:
            raise SmokeError(
                "wait-for-alert",
                f"no {service} alert matching {alert_name_contains!r} within {timeout}s",
            )
        sleep(interval)


def run(
    api_base: str,
    token: str,
    service: str,
    mode: str,
    expect_alert: str,
    expect_known: bool,
    minutes: int,
    timeout: float | None = None,
) -> dict:
    started = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    fault = set_fault(api_base, token, service, mode, minutes)
    print(f"fault set: service={fault['service']} mode={fault['mode']} until={fault['until']}")
    try:
        alert = wait_for_alert(
            api_base,
            token,
            service,
            expect_alert,
            not_before=started,
            timeout=timeout if timeout is not None else _ALERT_TIMEOUT_SECONDS,
            interval=_ALERT_POLL_SECONDS,
        )
        print(f"alert arrived: {alert['alert_id']} {alert['alert_name']} source={alert['source']}")
        alert = wait_for_verdict(api_base, token, alert["alert_id"], timeout=180, interval=5)
    finally:
        clear_fault(api_base, token, service)
        print(f"fault cleared on {service}")

    verdict = alert["verdict"]
    if verdict["model"] in ("stub", "cap"):
        raise SmokeError("verify-verdict", f"expected a real model, got {verdict['model']!r}")
    if expect_known and verdict.get("known") is not True:
        raise SmokeError("verify-verdict", f"expected known=true, got {verdict.get('known')!r}")
    return alert


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--service", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--expect-alert", required=True, help="substring of the alarm/rule name")
    parser.add_argument("--expect-known", action="store_true")
    parser.add_argument("--minutes", type=int, default=8)
    parser.add_argument(
        "--timeout",
        type=float,
        default=_ALERT_TIMEOUT_SECONDS,
        help="seconds to wait for the alert to arrive at the spine (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    api_base = os.environ.get("API_BASE", _DEFAULT_API_BASE)
    token = os.environ["SMOKE_TOKEN"]
    try:
        alert = run(
            api_base,
            token,
            args.service,
            args.mode,
            args.expect_alert,
            args.expect_known,
            args.minutes,
            args.timeout,
        )
    except SmokeError as exc:
        print(f"FAIL[{exc.step}]: {exc}", file=sys.stderr)
        return 1
    verdict = alert["verdict"]
    print(
        f"OK: alert_id={alert['alert_id']} alert={alert['alert_name']} "
        f"source={alert['source']} known={verdict.get('known')} action={verdict['action']} "
        f"model={verdict['model']}"
    )
    print(f"summary: {verdict.get('summary', '')[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
