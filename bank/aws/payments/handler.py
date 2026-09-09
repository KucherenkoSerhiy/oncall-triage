"""Lambda handler for `payments`: EventBridge schedule, every minute.

Normal path processes a batch of synthetic authorisations and hands each one
to `ledger` over SQS. Fault modes (set via the console API / bankops chaos)
simulate an upstream 503 burst, added latency, or a connection-pool
exhaustion - see `bank/aws/common.py` for the fault control plane.
"""

from __future__ import annotations

import json
import os
import random
import time
import uuid
from typing import Any

from bank.aws.common import current_fault, emit_metric, fail

_SERVICE = "payments"
_BATCH_SIZE = 5


def _authorisation() -> dict:
    return {
        "txn_id": str(uuid.uuid4()),
        "amount": round(random.uniform(1.0, 500.0), 2),  # noqa: S311 - synthetic demo data
        "currency": "EUR",
    }


def lambda_handler(event: dict, context: Any) -> dict:
    mode = current_fault(_SERVICE)

    if mode == "errors":
        fail("upstream issuer returned 503")
    if mode == "latency":
        time.sleep(2.5)
    if mode == "pool":
        emit_metric("PoolExhausted", 1, _SERVICE)
        fail("connection pool exhausted while authorizing payment")

    import boto3

    sqs = boto3.client("sqs")
    queue_url = os.environ["LEDGER_QUEUE_URL"]
    for _ in range(_BATCH_SIZE):
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(_authorisation()))

    return {"authorised": _BATCH_SIZE}
