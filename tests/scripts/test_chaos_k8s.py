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
