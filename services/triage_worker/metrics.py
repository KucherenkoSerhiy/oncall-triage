"""Custom metrics the triage worker emits (namespace ``Nordwind/Triage``).

Mirrors ``bank/aws/common.py``'s ``emit_metric``: ``cloudwatch:PutMetricData``
accepts no resource ARN, so the worker's IAM policy scopes it by the
``cloudwatch:namespace`` condition instead (``infra/aws/lambdas.tf``).
"""

from __future__ import annotations

_NAMESPACE = "Nordwind/Triage"


def emit_cap_reached() -> None:
    """Record that the daily LLM cap short-circuited a verdict."""
    import boto3

    client = boto3.client("cloudwatch")
    client.put_metric_data(
        Namespace=_NAMESPACE,
        MetricData=[
            {
                "MetricName": "CapReached",
                "Value": 1,
                "Dimensions": [{"Name": "estate", "Value": "all"}],
            }
        ],
    )
