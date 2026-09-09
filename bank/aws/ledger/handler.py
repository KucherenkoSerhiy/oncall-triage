"""Lambda handler for `ledger`: SQS event source, batch 5, ReportBatchItemFailures.

Normal path "posts" each authorisation message and reports no failures.
Fault modes simulate consumer lag (return every record as a failure so
messages stay in the queue and `ApproximateAgeOfOldestMessage` grows) or a
reconciliation mismatch (emit a metric, still process normally).
"""

from __future__ import annotations

from typing import Any

from bank.aws.common import current_fault, emit_metric

_SERVICE = "ledger"


def lambda_handler(event: dict, context: Any) -> dict:
    records = event.get("Records", [])
    mode = current_fault(_SERVICE)

    if mode == "lag":
        return {
            "batchItemFailures": [{"itemIdentifier": record["messageId"]} for record in records]
        }

    if mode == "reconciliation-mismatch":
        emit_metric("ReconciliationMismatch", 1, _SERVICE)

    return {"batchItemFailures": []}
