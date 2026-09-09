"""Lambda handler for the console API: API Gateway HTTP API v2 events."""

from __future__ import annotations

import json
import os
from typing import Any

from bank.aws.common import VALID_MODES
from services.console_api.auth import AuthError, check_bearer
from services.console_api.http import json_response, no_content_response, options_response
from services.console_api.store import ConsoleStore, FaultStore

_REQUIRED_FIELDS = ("service", "pattern", "explanation")


def _store() -> ConsoleStore:
    import boto3

    resource = boto3.resource("dynamodb")
    return ConsoleStore(
        resource.Table(os.environ["ALERTS_TABLE"]),
        resource.Table(os.environ["VERDICTS_TABLE"]),
        resource.Table(os.environ["KNOWN_ISSUES_TABLE"]),
    )


def _fault_store() -> FaultStore:
    import boto3

    resource = boto3.resource("dynamodb")
    return FaultStore(resource.Table(os.environ["BANK_FAULTS_TABLE"]))


def _origin() -> str:
    return os.environ["CONSOLE_ORIGIN"]


def _require_auth(event: dict) -> None:
    check_bearer(event.get("headers") or {}, os.environ["CONSOLE_TOKEN"])


def _handle_list_alerts(event: dict, store: ConsoleStore, origin: str) -> dict:
    params = event.get("queryStringParameters") or {}
    try:
        limit = int(params["limit"]) if params.get("limit") else 50
    except ValueError:
        return json_response(400, {"error": "limit must be an integer"}, origin)
    if not 1 <= limit <= 200:
        return json_response(400, {"error": "limit must be between 1 and 200"}, origin)
    return json_response(200, store.list_alerts(limit=limit), origin)


def _handle_get_alert(alert_id: str, store: ConsoleStore, origin: str) -> dict:
    alert = store.get_alert(alert_id)
    if alert is None:
        return json_response(404, {"error": "alert not found"}, origin)
    return json_response(200, alert, origin)


def _handle_list_known_issues(event: dict, store: ConsoleStore, origin: str) -> dict:
    params = event.get("queryStringParameters") or {}
    return json_response(200, store.list_known_issues(params.get("service")), origin)


def _handle_add_known_issue(event: dict, store: ConsoleStore, origin: str) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        return json_response(400, {"error": str(exc)}, origin)

    missing = [field for field in _REQUIRED_FIELDS if not body.get(field)]
    if missing:
        return json_response(400, {"error": f"missing fields: {', '.join(missing)}"}, origin)

    record = store.add_known_issue(
        service=body["service"],
        pattern=body["pattern"],
        explanation=body["explanation"],
        taught_by="console",
    )
    return json_response(201, record, origin)


def _handle_delete_known_issue(
    service: str, issue_id: str, store: ConsoleStore, origin: str
) -> dict:
    deleted = store.delete_known_issue(service, issue_id)
    if not deleted:
        return json_response(404, {"error": "known issue not found"}, origin)
    return no_content_response(origin)


def _handle_list_chaos(store: FaultStore, origin: str) -> dict:
    return json_response(200, store.list_faults(), origin)


def _handle_set_chaos(service: str, event: dict, store: FaultStore, origin: str) -> dict:
    if service not in VALID_MODES:
        return json_response(404, {"error": f"unknown service: {service}"}, origin)

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        return json_response(400, {"error": str(exc)}, origin)

    mode = body.get("mode")
    valid_modes = VALID_MODES[service]
    if mode not in valid_modes:
        error = f"invalid mode {mode!r} for {service}; valid modes: {', '.join(valid_modes)}"
        return json_response(400, {"error": error}, origin)

    minutes = body.get("minutes", 5)
    record = store.set_fault(service, mode, minutes, set_by="console")
    return json_response(201, record, origin)


def _handle_clear_chaos(service: str, store: FaultStore, origin: str) -> dict:
    if service not in VALID_MODES:
        return json_response(404, {"error": f"unknown service: {service}"}, origin)

    store.clear_fault(service)
    return no_content_response(origin)


def lambda_handler(event: dict, context: Any) -> dict:
    method = event["requestContext"]["http"]["method"]
    path = event["rawPath"]
    origin = _origin()

    if method == "OPTIONS":
        return options_response(origin)

    if method == "GET" and path == "/health":
        return json_response(200, {"ok": True}, origin)

    try:
        _require_auth(event)
    except AuthError as exc:
        return json_response(401, {"error": str(exc)}, origin)

    store = _store()
    segments = [segment for segment in path.split("/") if segment]

    if method == "GET" and segments == ["alerts"]:
        return _handle_list_alerts(event, store, origin)
    if method == "GET" and len(segments) == 2 and segments[0] == "alerts":
        return _handle_get_alert(segments[1], store, origin)
    if method == "GET" and segments == ["known-issues"]:
        return _handle_list_known_issues(event, store, origin)
    if method == "POST" and segments == ["known-issues"]:
        return _handle_add_known_issue(event, store, origin)
    if method == "DELETE" and len(segments) == 3 and segments[0] == "known-issues":
        return _handle_delete_known_issue(segments[1], segments[2], store, origin)
    if method == "GET" and segments == ["chaos"]:
        return _handle_list_chaos(_fault_store(), origin)
    if method == "POST" and len(segments) == 2 and segments[0] == "chaos":
        return _handle_set_chaos(segments[1], event, _fault_store(), origin)
    if method == "DELETE" and len(segments) == 2 and segments[0] == "chaos":
        return _handle_clear_chaos(segments[1], _fault_store(), origin)

    return json_response(404, {"error": "not found"}, origin)
