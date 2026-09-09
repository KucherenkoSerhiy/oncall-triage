"""Shared fault control plane for the AWS bank estate Lambdas.

Table schema (Terraform provisioning: ``infra/aws/bank.tf``): the
``BANK_FAULTS_TABLE`` DynamoDB table, hash key ``service`` (S). One item per
service currently under a fault: ``mode`` (S), ``until`` (N, epoch seconds),
``set_at`` (N, epoch seconds), ``set_by`` (S).
"""

from __future__ import annotations

import os
import time
from typing import NoReturn

_NAMESPACE = "Nordwind/Bank"

VALID_MODES: dict[str, tuple[str, ...]] = {
    "payments": ("errors", "latency", "pool"),
    "ledger": ("lag", "reconciliation-mismatch"),
    "auth": ("jwks-rotation", "lockouts"),
}


class BankFault(Exception):  # noqa: N818 - name fixed by the spec
    pass


def fail(message: str) -> NoReturn:
    raise BankFault(message)


def _faults_table() -> object:
    import boto3

    resource = boto3.resource("dynamodb")
    return resource.Table(os.environ["BANK_FAULTS_TABLE"])


def current_fault(service: str) -> str | None:
    response = _faults_table().get_item(Key={"service": service})  # type: ignore[attr-defined]
    item = response.get("Item")
    if item is None:
        return None
    if float(item.get("until", 0)) <= time.time():
        return None
    mode = item.get("mode")
    return str(mode) if mode is not None else None


def emit_metric(name: str, value: float, service: str) -> None:
    import boto3

    client = boto3.client("cloudwatch")
    client.put_metric_data(
        Namespace=_NAMESPACE,
        MetricData=[
            {
                "MetricName": name,
                "Value": value,
                "Dimensions": [{"Name": "service", "Value": service}],
            }
        ],
    )
