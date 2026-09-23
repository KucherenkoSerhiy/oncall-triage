"""Record the console's current view for visitors without a token (#131).

Writes ``snapshot.json`` = ``{recorded_at, run_url, alerts, known_issues}``
from ``GET /alerts?limit=50`` and ``GET /known-issues``, read with the smoke
token. The smoke job and estate-demo publish the file to the console bucket
as ``demo/snapshot.json`` (scripts/publish_snapshot.sh); the console renders
it read-only when no token is stored. The API itself stays token-only.

usage: python scripts/snapshot.py [OUT=snapshot.json]
env:   API_BASE (optional), SMOKE_TOKEN, GITHUB_* (optional - run_url)
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.smoke import _DEFAULT_API_BASE, SmokeError, http

_ALERT_LIMIT = 50
# Smoke probes fire on every deploy and would otherwise fill the top of the
# recording a visitor sees; estate alerts go first, then at most this many
# probes as proof the pipeline is exercised (#140).
_SMOKE_PREFIX = "SmokeTest"
_SMOKE_KEEP = 3


def _get(api_base: str, token: str, path: str, step: str) -> Any:
    status, body = http("GET", f"{api_base}{path}", headers={"Authorization": f"Bearer {token}"})
    if status != 200:
        raise SmokeError(step, f"HTTP {status}: {body!r}")
    return json.loads(body)


def run_url_from_env(env: Mapping[str, str] | None = None) -> str:
    """The Actions run that recorded the snapshot, or '' outside Actions."""
    if env is None:
        env = os.environ
    run_id = env.get("GITHUB_RUN_ID")
    repository = env.get("GITHUB_REPOSITORY")
    if not run_id or not repository:
        return ""
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    return f"{server}/{repository}/actions/runs/{run_id}"


def is_smoke(alert: dict[str, Any]) -> bool:
    return str(alert.get("alert_name", "")).startswith(_SMOKE_PREFIX)


def order_for_visitors(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Estate alerts in their original (newest-first) order, then a few smoke probes."""
    estate = [alert for alert in alerts if not is_smoke(alert)]
    smoke = [alert for alert in alerts if is_smoke(alert)]
    return estate + smoke[:_SMOKE_KEEP]


def build_snapshot(api_base: str, token: str, run_url: str = "") -> dict[str, Any]:
    alerts = _get(api_base, token, f"/alerts?limit={_ALERT_LIMIT}", "snapshot-alerts")
    known_issues = _get(api_base, token, "/known-issues", "snapshot-known-issues")
    if not isinstance(alerts, list) or not isinstance(known_issues, list):
        raise SmokeError("snapshot-shape", "expected JSON arrays from /alerts and /known-issues")
    return {
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_url": run_url,
        "alerts": order_for_visitors(alerts),
        "known_issues": known_issues,
    }


def main() -> int:
    api_base = os.environ.get("API_BASE", _DEFAULT_API_BASE)
    token = os.environ["SMOKE_TOKEN"]
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "snapshot.json")
    try:
        snapshot = build_snapshot(api_base, token, run_url_from_env())
    except SmokeError as exc:
        print(f"FAIL[{exc.step}]: {exc}", file=sys.stderr)
        return 1
    out.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    print(
        f"OK: snapshot {len(snapshot['alerts'])} alert(s), "
        f"{len(snapshot['known_issues'])} known issue(s) -> {out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
