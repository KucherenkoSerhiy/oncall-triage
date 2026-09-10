"""Unit tests for scripts/chaos_k8s.py (kubectl monkeypatched)."""

from __future__ import annotations

import json

from scripts import chaos_k8s


def test_patch_fault_builds_correct_command():
    calls = []

    def fake_run(argv, check=False):
        calls.append((argv, check))

    chaos_k8s.patch_fault("cards-authorization", "timeouts", run=fake_run)

    (argv, check) = calls[0]
    assert check is True
    assert argv[:6] == ["kubectl", "-n", "bank", "patch", "configmap", "nordwind-faults"]
    assert json.loads(argv[-1]) == {"data": {"cards-authorization": "timeouts"}}


def test_main_rejects_invalid_mode(monkeypatch, capsys):
    def fake_patch(service, mode, run=None):
        raise AssertionError("should not patch for an invalid mode")

    monkeypatch.setattr(chaos_k8s, "patch_fault", fake_patch)

    exit_code = chaos_k8s.main(["cards-authorization", "not-a-mode"])

    assert exit_code == 1
    assert "invalid mode" in capsys.readouterr().err


def test_main_clear_writes_empty_string(monkeypatch):
    captured = {}

    def fake_patch(service, mode, run=None):
        captured["service"] = service
        captured["mode"] = mode

    monkeypatch.setattr(chaos_k8s, "patch_fault", fake_patch)

    exit_code = chaos_k8s.main(["fraud-scoring", "clear"])

    assert exit_code == 0
    assert captured == {"service": "fraud-scoring", "mode": ""}


def test_main_valid_mode(monkeypatch):
    captured = {}

    def fake_patch(service, mode, run=None):
        captured["service"] = service
        captured["mode"] = mode

    monkeypatch.setattr(chaos_k8s, "patch_fault", fake_patch)

    exit_code = chaos_k8s.main(["open-banking-api", "cert-expiry"])

    assert exit_code == 0
    assert captured == {"service": "open-banking-api", "mode": "cert-expiry"}


def _recording_run():
    calls = []

    def fake_run(argv, check=False):
        calls.append((argv, check))

    return calls, fake_run


def test_pause_annotates_and_waits_for_the_paused_condition():
    calls, fake_run = _recording_run()

    chaos_k8s.pause_kafka_reconciliation(run=fake_run)

    assert [c for _, c in calls] == [True, True]
    assert calls[0][0] == [
        "kubectl",
        "-n",
        "bank",
        "annotate",
        "kafka",
        "nordwind-bank",
        "strimzi.io/pause-reconciliation=true",
        "--overwrite",
    ]
    assert calls[1][0][:5] == [
        "kubectl",
        "-n",
        "bank",
        "wait",
        "--for=condition=ReconciliationPaused",
    ]
    assert "kafka/nordwind-bank" in calls[1][0]


def test_wait_for_broker_ready_waits_for_the_podset_then_the_pod():
    calls, fake_run = _recording_run()

    chaos_k8s.wait_for_broker_ready(run=fake_run)

    assert calls[0][0][4] == "--for=create"
    assert "strimzipodset/nordwind-bank-broker" in calls[0][0]
    assert "strimzipodset/nordwind-bank-broker" in calls[1][0]
    assert calls[2][0] == [
        "kubectl",
        "-n",
        "bank",
        "wait",
        "--for=condition=Ready",
        "pod",
        "-l",
        "strimzi.io/pool-name=broker",
        "--timeout=600s",
    ]


def test_kafka_broker_down_pauses_then_deletes_the_broker_podset():
    # Scaling the broker pool to 0 is rejected by Strimzi in KRaft mode (#78):
    # the outage is produced by pausing reconciliation and deleting the PodSet.
    calls, fake_run = _recording_run()

    chaos_k8s.kafka_broker_down(run=fake_run)

    verbs = [argv[3] for argv, _ in calls]
    assert verbs == ["annotate", "wait", "delete"]
    assert calls[2][0][4:6] == ["strimzipodset", "nordwind-bank-broker"]
    assert all(check for _, check in calls)


def test_kafka_clear_resumes_reconciliation_then_waits():
    calls, fake_run = _recording_run()

    chaos_k8s.kafka_clear(run=fake_run)

    assert calls[0][0] == [
        "kubectl",
        "-n",
        "bank",
        "annotate",
        "kafka",
        "nordwind-bank",
        "strimzi.io/pause-reconciliation-",
        "--overwrite",
    ]
    assert [argv[3] for argv, _ in calls] == ["annotate", "wait", "wait", "wait"]


def test_main_kafka_broker_down(monkeypatch):
    calls = []
    monkeypatch.setattr(chaos_k8s, "kafka_broker_down", lambda: calls.append("broker-down"))
    monkeypatch.setattr(chaos_k8s, "kafka_clear", lambda: calls.append("clear"))

    exit_code = chaos_k8s.main(["kafka", "broker-down"])

    assert exit_code == 0
    assert calls == ["broker-down"]


def test_main_kafka_clear(monkeypatch):
    calls = []
    monkeypatch.setattr(chaos_k8s, "kafka_broker_down", lambda: calls.append("broker-down"))
    monkeypatch.setattr(chaos_k8s, "kafka_clear", lambda: calls.append("clear"))

    exit_code = chaos_k8s.main(["kafka", "clear"])

    assert exit_code == 0
    assert calls == ["clear"]


def test_main_kafka_rejects_invalid_mode(monkeypatch, capsys):
    monkeypatch.setattr(
        chaos_k8s, "kafka_broker_down", lambda: (_ for _ in ()).throw(AssertionError)
    )

    exit_code = chaos_k8s.main(["kafka", "not-a-mode"])

    assert exit_code == 1
    assert "invalid mode" in capsys.readouterr().err
