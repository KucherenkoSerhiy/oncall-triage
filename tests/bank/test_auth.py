from __future__ import annotations

import boto3
import pytest

from bank.aws.auth import handler
from bank.aws.common import BankFault
from tests.bank.conftest import put_fault


def test_normal_path_issues_20_tokens(moto_infra):
    assert handler.lambda_handler({}, None) == {"issued": 20}


def test_jwks_rotation_emits_metric_and_raises(moto_infra):
    put_fault(moto_infra, "auth", "jwks-rotation")

    with pytest.raises(BankFault, match="unknown key id kid-77"):
        handler.lambda_handler({}, None)

    cloudwatch = boto3.client("cloudwatch", region_name=moto_infra["region"])
    metrics = cloudwatch.list_metrics(Namespace="Nordwind/Bank")["Metrics"]
    assert any(m["MetricName"] == "AuthFailures" for m in metrics)


def test_lockouts_emits_metric_and_succeeds(moto_infra):
    put_fault(moto_infra, "auth", "lockouts")

    result = handler.lambda_handler({}, None)

    assert result == {"issued": 20}
    cloudwatch = boto3.client("cloudwatch", region_name=moto_infra["region"])
    metrics = cloudwatch.list_metrics(Namespace="Nordwind/Bank")["Metrics"]
    assert any(m["MetricName"] == "AccountLockouts" for m in metrics)
