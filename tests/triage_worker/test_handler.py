from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import boto3

from services.triage_worker import handler, metrics
from services.triage_worker.cap import DailyCap
from services.triage_worker.runner import TriageRunner
from tests.triage_worker.fake_llm import FakeLlm, build_scripted_agent_tree, text_response

_KNOWN_VERDICT_TEXT = (
    "Known issue: connection pool exhausted - Known scaling limit.\n"
    "```verdict\n"
    '{"known": true, "severity": "sev2", "action": "ack", "summary": "Known scaling limit"}\n'
    "```"
)


def _alerts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )


def _verdicts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["verdicts_table"]
    )


def _put_alert(moto_infra, alert_id, severity="sev2"):
    _alerts_table(moto_infra).put_item(
        Item={
            "alert_id": alert_id,
            "status": "queued",
            "received_at": "2024-01-01T00:00:00Z",
            "service": "svc",
            "alert_name": "HighLatency",
            "severity": severity,
            "title": "connection pool exhausted",
        }
    )


def _record(alert_id, message_id="msg-1"):
    return {"messageId": message_id, "body": json.dumps({"alert_id": alert_id})}


def _fake_runner(text=_KNOWN_VERDICT_TEXT):
    fake = FakeLlm(responses=[text_response(text)])
    tree = build_scripted_agent_tree(fake)
    return TriageRunner(agent_factory=lambda: tree)


def test_queued_alert_gets_verdict_and_becomes_triaged(moto_infra, monkeypatch):
    monkeypatch.setattr(handler, "_runner", _fake_runner())
    _put_alert(moto_infra, "A" * 26)

    result = handler.lambda_handler({"Records": [_record("A" * 26)]}, None)

    assert result["batchItemFailures"] == []

    verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert verdict["known"] is True
    assert verdict["severity"] == "sev2"
    assert verdict["action"] == "ack"
    assert verdict["summary"] == "Known scaling limit"
    assert verdict["model"] == "fake-1"
    assert verdict["verdict_parse_error"] is False
    assert "input_tokens" in verdict
    assert "output_tokens" in verdict

    alert = _alerts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert alert["status"] == "triaged"


def test_handler_logs_one_json_line_with_expected_fields(moto_infra, monkeypatch, caplog):
    monkeypatch.setattr(handler, "_runner", _fake_runner())
    _put_alert(moto_infra, "A" * 26)

    with caplog.at_level(logging.INFO, logger="services.triage_worker.handler"):
        handler.lambda_handler({"Records": [_record("A" * 26)]}, None)

    log_lines = [json.loads(r.message) for r in caplog.records if r.message.startswith("{")]
    assert len(log_lines) == 1
    line = log_lines[0]
    assert set(line) == {
        "alert_id",
        "known",
        "action",
        "input_tokens",
        "output_tokens",
        "duration_ms",
    }
    assert line["alert_id"] == "A" * 26
    assert line["known"] is True
    assert line["action"] == "ack"


def test_redelivered_message_does_not_overwrite_verdict(moto_infra, monkeypatch):
    monkeypatch.setattr(handler, "_runner", _fake_runner())
    _put_alert(moto_infra, "A" * 26)

    handler.lambda_handler({"Records": [_record("A" * 26, "msg-1")]}, None)
    first_verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]

    result = handler.lambda_handler({"Records": [_record("A" * 26, "msg-2")]}, None)

    assert result["batchItemFailures"] == []
    second_verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert second_verdict["created_at"] == first_verdict["created_at"]


def test_redelivered_message_does_not_call_model_or_consume_cap_slot(moto_infra, monkeypatch):
    call_count = 0
    fake = FakeLlm(responses=[text_response(_KNOWN_VERDICT_TEXT)])
    real_generate = FakeLlm.generate_content_async

    async def counting_generate(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        async for response in real_generate(self, *args, **kwargs):
            yield response

    monkeypatch.setattr(FakeLlm, "generate_content_async", counting_generate)
    tree = build_scripted_agent_tree(fake)
    monkeypatch.setattr(handler, "_runner", TriageRunner(agent_factory=lambda: tree))
    _put_alert(moto_infra, "A" * 26)

    today = datetime.now(UTC).date().isoformat()
    cap_key = {"alert_id": f"cap#{today}"}

    handler.lambda_handler({"Records": [_record("A" * 26, "msg-1")]}, None)
    calls_after_first = call_count
    cap_after_first = _verdicts_table(moto_infra).get_item(Key=cap_key)["Item"]["count"]

    handler.lambda_handler({"Records": [_record("A" * 26, "msg-2")]}, None)

    assert call_count == calls_after_first, "redelivery must not call the model again"
    cap_after_second = _verdicts_table(moto_infra).get_item(Key=cap_key)["Item"]["count"]
    assert cap_after_second == cap_after_first, "redelivery must not consume another cap slot"


def test_missing_alert_reported_in_batch_item_failures_others_succeed(moto_infra, monkeypatch):
    monkeypatch.setattr(handler, "_runner", _fake_runner())
    _put_alert(moto_infra, "A" * 26)

    event = {
        "Records": [
            _record("A" * 26, "msg-ok"),
            _record("Z" * 26, "msg-missing"),
        ]
    }

    result = handler.lambda_handler(event, None)

    assert result["batchItemFailures"] == [{"itemIdentifier": "msg-missing"}]
    verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert verdict["action"] == "ack"


def test_daily_cap_reached_writes_cap_verdict_without_calling_model(moto_infra, monkeypatch):
    monkeypatch.setenv("DAILY_ALERT_CAP", "1")
    # Consume the single slot directly against the same moto-backed table the
    # handler will see, so the handler's own DailyCap denies immediately -
    # the real (model-calling) default handler._runner is never invoked.
    verdicts_table = _verdicts_table(moto_infra)
    today = datetime.now(UTC).date().isoformat()
    assert DailyCap(verdicts_table).try_acquire(today) is True

    _put_alert(moto_infra, "A" * 26)

    result = handler.lambda_handler({"Records": [_record("A" * 26)]}, None)

    assert result["batchItemFailures"] == []
    verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert verdict["model"] == "cap"
    assert verdict["action"] == "monitor"
    assert verdict["summary"] == "Daily LLM cap reached; not triaged"

    alert = _alerts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert alert["status"] == "triaged"


def test_daily_cap_reached_calls_the_cap_reached_metric_emitter(moto_infra, monkeypatch):
    monkeypatch.setenv("DAILY_ALERT_CAP", "1")
    calls = []
    monkeypatch.setattr(metrics, "emit_cap_reached", lambda: calls.append(1))
    verdicts_table = _verdicts_table(moto_infra)
    today = datetime.now(UTC).date().isoformat()
    assert DailyCap(verdicts_table).try_acquire(today) is True

    _put_alert(moto_infra, "A" * 26)
    handler.lambda_handler({"Records": [_record("A" * 26)]}, None)

    assert calls == [1]


def test_normal_path_does_not_call_the_cap_reached_metric_emitter(moto_infra, monkeypatch):
    monkeypatch.setattr(handler, "_runner", _fake_runner())
    calls = []
    monkeypatch.setattr(metrics, "emit_cap_reached", lambda: calls.append(1))
    _put_alert(moto_infra, "A" * 26)

    result = handler.lambda_handler({"Records": [_record("A" * 26)]}, None)

    assert result["batchItemFailures"] == []
    assert calls == []
