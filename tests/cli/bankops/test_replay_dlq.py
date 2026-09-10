from __future__ import annotations

import argparse
import json

import boto3
import pytest
from moto import mock_aws

from cli.bankops import commands
from cli.bankops.commands import Config

_REGION = "eu-north-1"


@pytest.fixture
def moto_sqs(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", _REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")

    with mock_aws():
        sqs = boto3.client("sqs", region_name=_REGION)
        alerts_url = sqs.create_queue(QueueName="alerts")["QueueUrl"]
        dlq_url = sqs.create_queue(QueueName="alerts-dlq")["QueueUrl"]
        yield {"sqs": sqs, "alerts": alerts_url, "dlq": dlq_url}


def _config(moto_sqs) -> Config:
    return Config(
        api="https://api.example.com",
        hmac_secret="s",  # noqa: S106
        token="t",  # noqa: S106
        alerts_queue_url=moto_sqs["alerts"],
        alerts_dlq_url=moto_sqs["dlq"],
    )


def _send_dlq_messages(moto_sqs, n: int) -> None:
    for i in range(n):
        moto_sqs["sqs"].send_message(
            QueueUrl=moto_sqs["dlq"], MessageBody=json.dumps({"alert_id": f"A{i}"})
        )


def _dlq_message_count(moto_sqs) -> int:
    attrs = moto_sqs["sqs"].get_queue_attributes(
        QueueUrl=moto_sqs["dlq"],
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return int(attrs["ApproximateNumberOfMessages"]) + int(
        attrs["ApproximateNumberOfMessagesNotVisible"]
    )


def _alerts_message_count(moto_sqs) -> int:
    attrs = moto_sqs["sqs"].get_queue_attributes(
        QueueUrl=moto_sqs["alerts"], AttributeNames=["ApproximateNumberOfMessages"]
    )["Attributes"]
    return int(attrs["ApproximateNumberOfMessages"])


def test_moves_messages_with_yes(moto_sqs, capsys):
    _send_dlq_messages(moto_sqs, 3)

    exit_code = commands.cmd_replay_dlq(argparse.Namespace(max=10, yes=True), _config(moto_sqs))

    assert exit_code == 0
    assert _dlq_message_count(moto_sqs) == 0
    assert _alerts_message_count(moto_sqs) == 3
    out = capsys.readouterr().out
    assert "alert_id=A0" in out
    assert "moved 3 message(s)" in out


def test_without_yes_moves_nothing_and_prints_the_plan(moto_sqs, capsys):
    _send_dlq_messages(moto_sqs, 3)

    exit_code = commands.cmd_replay_dlq(argparse.Namespace(max=10, yes=False), _config(moto_sqs))

    assert exit_code == 0
    assert _dlq_message_count(moto_sqs) == 3
    assert _alerts_message_count(moto_sqs) == 0
    out = capsys.readouterr().out
    assert "would move alert_id=" in out
    assert "refusing to move 3 message(s) without --yes" in out


def test_max_limits_how_many_move(moto_sqs):
    _send_dlq_messages(moto_sqs, 3)

    exit_code = commands.cmd_replay_dlq(argparse.Namespace(max=2, yes=True), _config(moto_sqs))

    assert exit_code == 0
    assert _dlq_message_count(moto_sqs) == 1
    assert _alerts_message_count(moto_sqs) == 2


def test_empty_dlq_moves_nothing(moto_sqs, capsys):
    exit_code = commands.cmd_replay_dlq(argparse.Namespace(max=10, yes=True), _config(moto_sqs))

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "no messages" in out
