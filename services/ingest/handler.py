"""Lambda handler for alert ingest: API Gateway HTTP API v2 and SNS events."""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from services.ingest.adapters import NotAnAlert, alertmanager, azure_monitor, bankops, cloudwatch
from services.ingest.canonical import CanonicalAlert
from services.ingest.dedup import AlertStore
from services.ingest.hmac_auth import HmacError, verify
from services.ingest.scrub import scrub_alert

logger = logging.getLogger(__name__)
# The Lambda runtime pre-configures the root handler at WARNING; without this
# the per-alert JSON line (requirement 7) never reaches CloudWatch.
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_ADAPTERS = {
    "bankops": bankops.to_canonical,
    "cloudwatch": cloudwatch.to_canonical,
    "azure-monitor": azure_monitor.to_canonical,
}


def _sqs_client() -> Any:
    import boto3

    return boto3.client("sqs")


def _alert_store() -> AlertStore:
    return AlertStore(os.environ["ALERTS_TABLE"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _process_alert(alert: CanonicalAlert, store: AlertStore) -> dict:
    scrubbed = scrub_alert(alert)
    existing = store.find_open(scrubbed.fingerprint, scrubbed.received_at)
    if existing is not None:
        store.bump(existing["alert_id"], scrubbed.received_at)
        deduped = True
    else:
        store.put_new(scrubbed)
        _sqs_client().send_message(
            QueueUrl=os.environ["ALERTS_QUEUE_URL"],
            MessageBody=json.dumps({"alert_id": scrubbed.alert_id}),
        )
        deduped = False

    logger.info(
        json.dumps(
            {
                "alert_id": scrubbed.alert_id,
                "source": scrubbed.source,
                "service": scrubbed.service,
                "deduped": deduped,
            }
        )
    )
    return {"alert_id": scrubbed.alert_id, "fingerprint": scrubbed.fingerprint, "deduped": deduped}


def _alerts_for(source: str, payload: dict, received_at: str) -> list[CanonicalAlert]:
    if source == "alertmanager":
        alerts = alertmanager.to_canonical_many(payload, received_at)
        if not alerts:
            raise NotAnAlert("no firing alerts in payload")
        return alerts
    if source in _ADAPTERS:
        return [_ADAPTERS[source](payload, received_at)]
    raise ValueError(f"source: unknown source {source!r}")


def _handle_http(event: dict) -> dict:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    raw_body = event.get("body") or ""
    body_bytes = base64.b64decode(raw_body) if event.get("isBase64Encoded") else raw_body.encode()

    secret = os.environ["INGEST_HMAC_SECRET"].encode()
    timestamp = headers.get("x-nordwind-timestamp", "")
    signature = headers.get("x-nordwind-signature", "")
    try:
        verify(secret, timestamp, body_bytes, signature)
    except HmacError as exc:
        return {"statusCode": 401, "body": json.dumps({"error": str(exc)})}

    try:
        body = json.loads(body_bytes)
        source = body["source"]
        adapter_payload = body["payload"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": str(exc)})}

    received_at = _now_iso()
    try:
        alerts = _alerts_for(source, adapter_payload, received_at)
    except NotAnAlert as exc:
        return {"statusCode": 422, "body": json.dumps({"error": str(exc)})}
    except ValueError as exc:
        return {"statusCode": 400, "body": json.dumps({"error": str(exc)})}

    store = _alert_store()
    results = [_process_alert(alert, store) for alert in alerts]
    return {"statusCode": 202, "body": json.dumps({"results": results})}


def _handle_sns(event: dict) -> dict:
    received_at = _now_iso()
    store = _alert_store()
    results = []
    for record in event["Records"]:
        message = json.loads(record["Sns"]["Message"])
        try:
            alert = cloudwatch.to_canonical(message, received_at)
        except NotAnAlert:
            continue
        results.append(_process_alert(alert, store))
    return {"results": results}


def lambda_handler(event: dict, context: Any) -> dict:
    records = event.get("Records")
    if records and "Sns" in records[0]:
        return _handle_sns(event)
    return _handle_http(event)
