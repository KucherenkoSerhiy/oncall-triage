"""Live chaos scenarios for the Kubernetes bank estate (stdlib only).

Like `scripts/chaos_probe.py` for AWS/Azure, but the fault is set through the
`nordwind-faults` ConfigMap (`kubectl patch`) instead of the console API's
`/chaos` route, and the first hop is a wait on Alertmanager itself - only
once Prometheus's own rule is firing does the alert have a chance of
reaching the triage spine.

    python scripts/estate_scenarios.py --scenario cards-timeouts

Run by `task estate-demo` against a local kind cluster, and by
`.github/workflows/estate-demo.yml`. Reuses `scripts/chaos_probe.py`'s `http`
helper and `scripts/smoke.py`'s `SmokeError` / default API base.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.chaos_probe import http
from scripts.smoke import _DEFAULT_API_BASE, SmokeError

_DEFAULT_ALERTMANAGER = "http://localhost:9093"
_ALERT_TIMEOUT_SECONDS = 480
_ALERT_POLL_SECONDS = 10
_VERDICT_TIMEOUT_SECONDS = 600
_VERDICT_POLL_SECONDS = 5

_M7_SCENARIOS = ("fraud-lag", "broker-down")
_SCENARIOS = ("cards-timeouts", *_M7_SCENARIOS)


def set_fault(service: str, mode: str, run=subprocess.run) -> None:
    patch = json.dumps({"data": {service: mode}})
    run(
        [
            "kubectl",
            "-n",
            "bank",
            "patch",
            "configmap",
            "nordwind-faults",
            "--type",
            "merge",
            "-p",
            patch,
        ],
        check=True,
    )


def clear_fault(service: str, run=subprocess.run) -> None:
    set_fault(service, "", run=run)


def wait_for_rule_firing(
    alertmanager: str,
    alert_name: str,
    timeout: float = _ALERT_TIMEOUT_SECONDS,
    interval: float = _ALERT_POLL_SECONDS,
    sleep=time.sleep,
    now=time.monotonic,
) -> dict:
    """Poll Alertmanager until `alert_name` appears in the active alerts."""
    deadline = now() + timeout
    while True:
        status, body = http("GET", f"{alertmanager}/api/v2/alerts?active=true")
        if status != 200:
            raise SmokeError("wait-for-rule", f"HTTP {status} from Alertmanager: {body!r}")
        for alert in json.loads(body):
            if alert.get("labels", {}).get("alertname") == alert_name:
                return alert
        if now() >= deadline:
            raise SmokeError(
                "wait-for-rule", f"{alert_name} rule never fired in Alertmanager within {timeout}s"
            )
        sleep(interval)


def wait_for_spine_verdict(
    api_base: str,
    token: str,
    estate: str,
    service: str,
    alert_name: str,
    not_before: str,
    timeout: float = _VERDICT_TIMEOUT_SECONDS,
    interval: float = _VERDICT_POLL_SECONDS,
    sleep=time.sleep,
    now=time.monotonic,
) -> dict:
    """Return the first alert matching estate/service/alert_name received
    after `not_before` once it carries a verdict.

    Distinguishes "the alert never reached the spine at all" (Alertmanager
    never delivered route B) from "it arrived but has no verdict yet" so
    `main` can report which hop failed.
    """
    headers = {"Authorization": f"Bearer {token}"}
    deadline = now() + timeout
    seen_alert = False
    while True:
        status, body = http("GET", f"{api_base}/alerts?limit=100", headers=headers)
        if status != 200:
            raise SmokeError("wait-for-verdict", f"HTTP {status}: {body!r}")
        for alert in json.loads(body):
            if (
                alert.get("estate") == estate
                and alert.get("service") == service
                and alert.get("alert_name") == alert_name
                and (alert.get("received_at") or "") >= not_before
            ):
                seen_alert = True
                if alert.get("verdict") is not None:
                    return alert
        if now() >= deadline:
            if not seen_alert:
                raise SmokeError(
                    "wait-for-verdict",
                    f"Alertmanager never delivered {estate}/{service}/{alert_name} "
                    f"to the spine within {timeout}s",
                )
            raise SmokeError(
                "wait-for-verdict",
                f"no verdict for {estate}/{service}/{alert_name} within {timeout}s",
            )
        sleep(interval)


def run_cards_timeouts(
    alertmanager: str,
    api_base: str,
    token: str,
    alert_timeout: float = _ALERT_TIMEOUT_SECONDS,
    verdict_timeout: float = _VERDICT_TIMEOUT_SECONDS,
    run=subprocess.run,
) -> dict:
    service = "cards-authorization"
    mode = "timeouts"
    alert_name = "CardsAuthHighLatency"

    started = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    set_fault(service, mode, run=run)
    print(f"fault set: service={service} mode={mode}")
    try:
        wait_for_rule_firing(alertmanager, alert_name, timeout=alert_timeout)
        print(f"{alert_name} firing in Alertmanager")
        alert = wait_for_spine_verdict(
            api_base,
            token,
            "kubernetes",
            service,
            alert_name,
            not_before=started,
            timeout=verdict_timeout,
        )
    finally:
        clear_fault(service, run=run)
        print(f"fault cleared on {service}")
    return alert


_RUNNERS = {"cards-timeouts": run_cards_timeouts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scenario", required=True, choices=[*_SCENARIOS, "list"])
    parser.add_argument(
        "--alertmanager", default=os.environ.get("ALERTMANAGER_URL", _DEFAULT_ALERTMANAGER)
    )
    parser.add_argument("--alert-timeout", type=float, default=_ALERT_TIMEOUT_SECONDS)
    parser.add_argument("--verdict-timeout", type=float, default=_VERDICT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)

    if args.scenario == "list":
        print("cards-timeouts (M6)")
        for name in _M7_SCENARIOS:
            print(f"{name} (M7)")
        return 0

    if args.scenario in _M7_SCENARIOS:
        print(f"FAIL: {args.scenario!r} is registered for M7, not implemented yet", file=sys.stderr)
        return 2

    api_base = os.environ.get("API_BASE", _DEFAULT_API_BASE)
    token = os.environ["SMOKE_TOKEN"]

    try:
        alert = _RUNNERS[args.scenario](
            args.alertmanager, api_base, token, args.alert_timeout, args.verdict_timeout
        )
    except SmokeError as exc:
        print(f"FAIL[{exc.step}]: {exc}", file=sys.stderr)
        return 1

    verdict = alert["verdict"]
    print(
        f"OK: alert_id={alert['alert_id']} alert={alert['alert_name']} "
        f"known={verdict.get('known')} action={verdict['action']} model={verdict['model']}"
    )
    print(f"summary: {verdict.get('summary', '')[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
