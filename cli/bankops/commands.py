"""bankops subcommands: fire, tail, teach, known."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from bank.aws.common import VALID_MODES
from cli.bankops import client
from services.ingest.hmac_auth import sign

_COLUMNS = ("TIME", "SEV", "ESTATE", "SERVICE", "ALERT", "STATUS", "OCC", "VERDICT")
_WIDTHS = (8, 5, 11, 20, 28, 8, 4, 12)

_CHAOS_COLUMNS = ("SERVICE", "MODE", "MIN LEFT")
_CHAOS_WIDTHS = (12, 24, 10)


@dataclass
class Config:
    api: str
    hmac_secret: str
    token: str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _auth_headers(config: Config) -> dict:
    return {"Authorization": f"Bearer {config.token}"}


def cmd_fire(args: argparse.Namespace, config: Config) -> int:
    labels = dict(kv.split("=", 1) for kv in args.label) if args.label else {}
    payload = {
        "source": "bankops",
        "estate": args.estate,
        "service": args.service,
        "alert_name": args.alert,
        "severity": args.severity,
        "title": args.title or args.alert,
        "description": args.description or "",
        "sample_logs": args.log or [],
        "labels": labels,
        "fired_at": _now_iso(),
    }
    body = json.dumps({"source": "bankops", "payload": payload}).encode()
    timestamp = str(int(time.time()))
    signature = sign(config.hmac_secret.encode(), timestamp, body)
    headers = {
        "Content-Type": "application/json",
        "X-Nordwind-Timestamp": timestamp,
        "X-Nordwind-Signature": signature,
    }

    try:
        response_body = client.request("POST", f"{config.api}/alerts", headers=headers, body=body)
    except client.BankopsError as exc:
        print(f"error: {exc.body}")
        return 1

    entry = json.loads(response_body)["results"][0]
    print(f"alert_id={entry['alert_id']} deduped={entry['deduped']}")
    return 0


def _format_row(values: tuple, widths: tuple = _WIDTHS) -> str:
    return "".join(f"{value!s:<{width}}" for value, width in zip(values, widths, strict=True))


def _format_table(alerts: list[dict]) -> str:
    lines = [_format_row(_COLUMNS)]
    for alert in alerts:
        received = datetime.fromisoformat(alert["received_at"].replace("Z", "+00:00"))
        verdict = alert.get("verdict") or {}
        lines.append(
            _format_row(
                (
                    received.strftime("%H:%M:%S"),
                    alert["severity"],
                    alert["estate"],
                    alert["service"],
                    alert["alert_name"],
                    alert["status"],
                    alert.get("occurrences", 0),
                    verdict.get("action", "-"),
                )
            )
        )
    return "\n".join(lines)


def cmd_tail(args: argparse.Namespace, config: Config) -> int:
    url = f"{config.api}/alerts?limit={args.limit}"

    def _render() -> None:
        body = client.request("GET", url, headers=_auth_headers(config))
        print(_format_table(json.loads(body)))

    if not args.watch:
        _render()
        return 0

    try:
        while True:
            _render()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_teach(args: argparse.Namespace, config: Config) -> int:
    body = json.dumps(
        {"service": args.service, "pattern": args.pattern, "explanation": args.explanation}
    ).encode()
    headers = {"Content-Type": "application/json", **_auth_headers(config)}

    try:
        response_body = client.request(
            "POST", f"{config.api}/known-issues", headers=headers, body=body
        )
    except client.BankopsError as exc:
        print(f"error: {exc.body}")
        return 1

    record = json.loads(response_body)
    print(f"issue_id={record['issue_id']} service={record['service']}")
    return 0


def cmd_known(args: argparse.Namespace, config: Config) -> int:
    url = f"{config.api}/known-issues"
    if args.service:
        url += f"?service={args.service}"

    body = client.request("GET", url, headers=_auth_headers(config))
    for issue in json.loads(body):
        print(f"{issue['service']:<20}{issue['pattern']:<40}{issue['explanation']}")
    return 0


def _print_chaos_status(config: Config) -> None:
    body = client.request("GET", f"{config.api}/chaos", headers=_auth_headers(config))
    faults = json.loads(body)
    print(_format_row(_CHAOS_COLUMNS, _CHAOS_WIDTHS))
    for fault in faults:
        remaining = max(0, int((fault["until"] - time.time()) // 60))
        print(_format_row((fault["service"], fault["mode"], remaining), _CHAOS_WIDTHS))


def cmd_chaos(args: argparse.Namespace, config: Config) -> int:
    if args.status:
        _print_chaos_status(config)
        return 0

    if not args.service:
        print("error: service is required unless --status is given")
        return 1

    if args.clear:
        try:
            client.request(
                "DELETE", f"{config.api}/chaos/{args.service}", headers=_auth_headers(config)
            )
        except client.BankopsError as exc:
            print(f"error: {exc.body}")
            return 1
        print(f"cleared fault on {args.service}")
        return 0

    valid_modes = VALID_MODES.get(args.service)
    if valid_modes is None:
        print(f"error: unknown service {args.service!r}; valid services: {', '.join(VALID_MODES)}")
        return 1
    if not args.mode:
        print("error: --mode or --clear is required")
        return 1
    if args.mode not in valid_modes:
        print(
            f"error: invalid mode {args.mode!r} for {args.service}; "
            f"valid modes: {', '.join(valid_modes)}"
        )
        return 1

    body = json.dumps({"mode": args.mode, "minutes": args.minutes}).encode()
    headers = {"Content-Type": "application/json", **_auth_headers(config)}

    try:
        response_body = client.request(
            "POST", f"{config.api}/chaos/{args.service}", headers=headers, body=body
        )
    except client.BankopsError as exc:
        print(f"error: {exc.body}")
        return 1

    record = json.loads(response_body)
    print(f"service={record['service']} mode={record['mode']} until={record['until']}")
    return 0
