"""Daily cap on triaged alerts, to bound worst-case LLM spend.

One item per day in the verdicts table, keyed ``alert_id = "cap#YYYY-MM-DD"``,
with an atomic counter increment conditioned on staying under the cap.
"""

from __future__ import annotations

import os
from typing import Any

from botocore.exceptions import ClientError

_CAP_KEY_PREFIX = "cap#"
_DEFAULT_CAP = 500


class DailyCap:
    def __init__(self, verdicts_table: Any) -> None:
        self._table = verdicts_table
        self._cap = int(os.environ.get("DAILY_ALERT_CAP", _DEFAULT_CAP))

    def try_acquire(self, today: str) -> bool:
        """Atomically claim one slot in today's cap. False once the cap is hit."""
        try:
            self._table.update_item(
                Key={"alert_id": f"{_CAP_KEY_PREFIX}{today}"},
                UpdateExpression="ADD #count :one",
                ConditionExpression="attribute_not_exists(#count) OR #count < :cap",
                ExpressionAttributeNames={"#count": "count"},
                ExpressionAttributeValues={":one": 1, ":cap": self._cap},
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            return False
        return True
