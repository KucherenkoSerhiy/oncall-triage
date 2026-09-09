"""API Gateway HTTP API v2 response helpers, including CORS."""

from __future__ import annotations

import json
from decimal import Decimal


def _cors_headers(origin: str) -> dict:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    }


def _json_default(value: object) -> int | float:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"not JSON serializable: {value!r}")


def json_response(status: int, body: dict | list, origin: str) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **_cors_headers(origin)},
        "body": json.dumps(body, default=_json_default),
    }


def no_content_response(origin: str) -> dict:
    return {
        "statusCode": 204,
        "headers": _cors_headers(origin),
        "body": "",
    }


def options_response(origin: str) -> dict:
    return no_content_response(origin)
