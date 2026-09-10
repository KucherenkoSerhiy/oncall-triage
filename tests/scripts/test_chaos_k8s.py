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


def test_scale_kafka_node_pool_builds_correct_command():
    calls = []

    def fake_run(argv, check=False):
        calls.append((argv, check))

    chaos_k8s.scale_kafka_node_pool(0, run=fake_run)

    (argv, check) = calls[0]
    assert check is True
    assert argv[:6] == ["kubectl", "-n", "bank", "patch", "kafkanodepool", "broker"]
    assert json.loads(argv[-1]) == {"spec": {"replicas": 0}}


def test_wait_for_broker_ready_builds_correct_command():
    calls = []

    def fake_run(argv, check=False):
        calls.append((argv, check))

    chaos_k8s.wait_for_broker_ready(run=fake_run)

    (argv, check) = calls[0]
    assert check is True
    assert argv == [
        "kubectl",
        "-n",
        "bank",
        "wait",
        "--for=condition=Ready",
        "pod",
        "-l",
        "strimzi.io/pool-name=broker",
        "--timeout=180s",
    ]


def test_kafka_broker_down_scales_to_zero(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        chaos_k8s,
        "scale_kafka_node_pool",
        lambda replicas, run=None: captured.update(replicas=replicas),
    )

    chaos_k8s.kafka_broker_down()

    assert captured == {"replicas": 0}


def test_kafka_clear_scales_to_one_and_waits(monkeypatch):
    calls = []
    monkeypatch.setattr(
        chaos_k8s,
        "scale_kafka_node_pool",
        lambda replicas, run=None: calls.append(("scale", replicas)),
    )
    monkeypatch.setattr(
        chaos_k8s, "wait_for_broker_ready", lambda run=None: calls.append(("wait",))
    )

    chaos_k8s.kafka_clear()

    assert calls == [("scale", 1), ("wait",)]


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
