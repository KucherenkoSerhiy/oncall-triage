"""Post-deploy smoke probe (stdlib only - runs before dev deps are installed).

Checks `/health`, fires one synthetic `bankops` alert signed with the real
HMAC secret, and polls for a verdict. Called by the `smoke` job in
`.github/workflows/deploy.yml` after `terraform apply`.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.ingest.hmac_auth import sign

_DEFAULT_API_BASE = "https://api.triage.serhiykucherenko.dev"
_POLL_TIMEOUT_SECONDS = 90
_POLL_INTERVAL_SECONDS = 3
_HTTP_TIMEOUT_SECONDS = 10


class SmokeError(Exception):
    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step


def http(
    method: str, url: str, headers: dict | None = None, body: bytes | None = None
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=body)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def check_health(api_base: str) -> None:
    status, body = http("GET", f"{api_base}/health")
    if status != 200:
        raise SmokeError("health", f"HTTP {status}: {body!r}")


def fire_alert(api_base: str, hmac_secret: str) -> str:
    payload = {
        "source": "bankops",
        "estate": "aws",
        "service": "smoke",
        "alert_name": "SmokeTest",
        "severity": "sev4",
        "title": "SmokeTest",
        "description": "deploy.yml smoke probe",
        "sample_logs": [],
        "labels": {},
        "fired_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    body = json.dumps({"source": "bankops", "payload": payload}).encode()
    timestamp = str(int(time.time()))
    signature = sign(hmac_secret.encode(), timestamp, body)
    headers = {
        "Content-Type": "application/json",
        "X-Nordwind-Timestamp": timestamp,
        "X-Nordwind-Signature": signature,
    }

    status, response_body = http("POST", f"{api_base}/alerts", headers=headers, body=body)
    if status != 202:
        raise SmokeError("fire-alert", f"HTTP {status}: {response_body!r}")
    return json.loads(response_body)["results"][0]["alert_id"]


def wait_for_verdict(
    api_base: str,
    token: str,
    alert_id: str,
    timeout: float = _POLL_TIMEOUT_SECONDS,
    interval: float = _POLL_INTERVAL_SECONDS,
    sleep=time.sleep,
    now=time.monotonic,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    deadline = now() + timeout
    while True:
        status, body = http("GET", f"{api_base}/alerts/{alert_id}", headers=headers)
        if status == 200:
            alert = json.loads(body)
            if alert.get("verdict") is not None:
                return alert
        elif status != 404:
            raise SmokeError("wait-for-verdict", f"HTTP {status}: {body!r}")

        if now() >= deadline:
            raise SmokeError("wait-for-verdict", f"no verdict for {alert_id} within {timeout}s")
        sleep(interval)


def main() -> int:
    api_base = os.environ.get("API_BASE", _DEFAULT_API_BASE)
    hmac_secret = os.environ["SMOKE_HMAC_SECRET"]
    token = os.environ["SMOKE_TOKEN"]

    try:
        check_health(api_base)
        alert_id = fire_alert(api_base, hmac_secret)
        alert = wait_for_verdict(api_base, token, alert_id)
    except SmokeError as exc:
        print(f"FAIL[{exc.step}]: {exc}", file=sys.stderr)
        return 1

    print(f"OK: alert_id={alert_id} verdict_action={alert['verdict']['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
