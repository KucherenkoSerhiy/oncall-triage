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

from scripts import chaos_k8s
from scripts.chaos_probe import http
from scripts.smoke import _DEFAULT_API_BASE, SmokeError

_DEFAULT_ALERTMANAGER = "http://localhost:9093"
_ALERT_TIMEOUT_SECONDS = 480
_ALERT_POLL_SECONDS = 10
_VERDICT_TIMEOUT_SECONDS = 600
_VERDICT_POLL_SECONDS = 5
# broker-down's last hop (kafka clear -> broker pod Ready again) has its own
# budget, separate from the alert/verdict waits above.
_BROKER_READY_TIMEOUT_SECONDS = 300

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
                # The list endpoint carries no verdicts (services/console_api
                # store.list_alerts); only GET /alerts/{id} joins the verdict
                # table - the first demo waited 10 min on a verdict that had
                # landed after 15 s (#68).
                status, one = http("GET", f"{api_base}/alerts/{alert['alert_id']}", headers=headers)
                if status == 200:
                    detailed = json.loads(one)
                    if detailed.get("verdict") is not None:
                        return detailed
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


def _require_route(alert: dict, expected: str) -> dict:
    """Fail loudly if the verdict's alert did not travel the expected route.

    `services/ingest/adapters/alertmanager.py` stamps `labels.route` ("A" if
    the Alertmanager receiver name contains "kafka", else "B") on every
    canonical alert - this is the one place a scenario can prove which path
    an alert actually took, not just that a verdict eventually showed up.
    """
    route = alert.get("labels", {}).get("route")
    if route != expected:
        raise SmokeError(
            "wrong-route",
            f"alert_id={alert['alert_id']} took route {route!r}, expected {expected!r}",
        )
    return alert


def run_fraud_lag(
    alertmanager: str,
    api_base: str,
    token: str,
    alert_timeout: float = _ALERT_TIMEOUT_SECONDS,
    verdict_timeout: float = _VERDICT_TIMEOUT_SECONDS,
    run=subprocess.run,
) -> dict:
    """`lag` on fraud-scoring -> KafkaConsumerLag -> route A (over Kafka)."""
    service = "fraud-scoring"
    mode = "lag"
    alert_name = "KafkaConsumerLag"

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
        _require_route(alert, "A")
    finally:
        clear_fault(service, run=run)
        print(f"fault cleared on {service}")
    return alert


def run_broker_down(
    alertmanager: str,
    api_base: str,
    token: str,
    alert_timeout: float = _ALERT_TIMEOUT_SECONDS,
    verdict_timeout: float = _VERDICT_TIMEOUT_SECONDS,
    run=subprocess.run,
) -> dict:
    """kafka broker-down -> KafkaBrokerDown -> route B (the alert about
    Kafka can't reliably travel over the thing it's reporting broken)."""
    service = "kafka"
    alert_name = "KafkaBrokerDown"

    started = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    chaos_k8s.kafka_broker_down(run=run)
    print("fault set: service=kafka mode=broker-down")
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
        _require_route(alert, "B")
    finally:
        chaos_k8s.scale_kafka_node_pool(1, run=run)
        chaos_k8s.wait_for_broker_ready(run=run, timeout=f"{_BROKER_READY_TIMEOUT_SECONDS}s")
        print("kafka broker cleared, pod Ready")
    return alert


_RUNNERS = {
    "cards-timeouts": run_cards_timeouts,
    "fraud-lag": run_fraud_lag,
    "broker-down": run_broker_down,
}


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
    route = alert.get("labels", {}).get("route")
    print(
        f"OK: alert_id={alert['alert_id']} alert={alert['alert_name']} route={route} "
        f"known={verdict.get('known')} action={verdict['action']} model={verdict['model']}"
    )
    print(f"summary: {verdict.get('summary', '')[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
