"""Print Kubernetes bank estate status (stdlib only, like scripts/smoke.py).

Pods in `bank` and `monitoring`, the `nordwind-faults` ConfigMap contents,
and firing alerts from the Alertmanager API. Run by `task estate-status`
against a live kind cluster (`task estate-up`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

_DEFAULT_ALERTMANAGER = "http://localhost:9093"
_HTTP_TIMEOUT_SECONDS = 10


def kubectl(*args: str, run=subprocess.run) -> str:
    result = run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def http(method: str, url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method=method)  # noqa: S310 - fixed local Alertmanager URL
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def print_pods(namespace: str, out=sys.stdout) -> None:
    print(f"--- pods: {namespace} ---", file=out)
    print(kubectl("-n", namespace, "get", "pods").rstrip("\n"), file=out)


def print_faults(out=sys.stdout) -> None:
    print("--- faults (nordwind-faults ConfigMap) ---", file=out)
    raw = kubectl("-n", "bank", "get", "configmap", "nordwind-faults", "-o", "json")
    data = json.loads(raw).get("data", {})
    for service, mode in sorted(data.items()):
        print(f"{service:<20}{mode or '(normal)'}", file=out)


def print_firing_alerts(alertmanager: str, out=sys.stdout) -> None:
    print("--- firing alerts (Alertmanager) ---", file=out)
    status, body = http("GET", f"{alertmanager}/api/v2/alerts?active=true")
    if status != 200:
        print(f"error: HTTP {status} from Alertmanager", file=out)
        return

    alerts = json.loads(body)
    if not alerts:
        print("(none firing)", file=out)
        return

    print(f"{'NAME':<28}{'SERVICE':<20}{'SEVERITY':<10}STARTED", file=out)
    for alert in alerts:
        labels = alert.get("labels", {})
        print(
            f"{labels.get('alertname', '?'):<28}{labels.get('service', '?'):<20}"
            f"{labels.get('severity', '?'):<10}{alert.get('startsAt', '?')}",
            file=out,
        )


def print_forwarder_hint(out=sys.stdout) -> None:
    if not os.environ.get("FORWARDER_URL"):
        print("--- forwarder ---", file=out)
        print(
            "FORWARDER_URL is not set: route B goes to the dummy receiver "
            "(http://127.0.0.1:9/) - alerts fire but never leave the cluster.",
            file=out,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alertmanager",
        default=os.environ.get("ALERTMANAGER_URL", _DEFAULT_ALERTMANAGER),
    )
    args = parser.parse_args(argv)

    print_pods("bank")
    print_pods("monitoring")
    print_faults()
    print_firing_alerts(args.alertmanager)
    print_forwarder_hint()
    return 0


if __name__ == "__main__":
    sys.exit(main())
