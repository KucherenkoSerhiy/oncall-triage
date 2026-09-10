from __future__ import annotations

import argparse
import json

from cli.bankops import client, commands
from cli.bankops.commands import Config

CONFIG = Config(
    api="https://api.example.com",
    hmac_secret="test-secret",  # noqa: S106
    token="test-token",  # noqa: S106
)


def _export_file(tmp_path, items: list[dict]) -> str:
    path = tmp_path / "export.json"
    path.write_text(
        json.dumps({"exported_at": "2026-01-01T00:00:00Z", "count": len(items), "items": items})
    )
    return str(path)


def _args(file: str, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(file=file, dry_run=dry_run)


def test_dry_run_prints_and_posts_nothing(tmp_path, monkeypatch, capsys):
    calls = []

    def fake_request(method, url, headers=None, body=None):
        calls.append(method)
        assert method == "GET"
        return json.dumps([]).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    file_path = _export_file(
        tmp_path, [{"service": "payments-api", "pattern": "p", "explanation": "e"}]
    )

    exit_code = commands.cmd_known_issues_import(_args(file_path, dry_run=True), CONFIG)

    assert exit_code == 0
    assert calls == ["GET"]  # only the existing-issues fetch, no POST
    out = capsys.readouterr().out
    assert "would import" in out
    assert "imported=1 skipped=0 failed=0" in out


def test_duplicate_service_and_pattern_is_skipped(tmp_path, monkeypatch, capsys):
    def fake_request(method, url, headers=None, body=None):
        if method == "GET":
            return json.dumps(
                [{"service": "payments-api", "pattern": "p", "explanation": "e"}]
            ).encode()
        raise AssertionError("must not POST a known issue that already exists")

    monkeypatch.setattr(commands.client, "request", fake_request)

    file_path = _export_file(
        tmp_path, [{"service": "payments-api", "pattern": "p", "explanation": "e"}]
    )

    exit_code = commands.cmd_known_issues_import(_args(file_path), CONFIG)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "imported=0 skipped=1 failed=0" in out


def test_successful_import_posts_the_item_and_counts_it(tmp_path, monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, body=None):
        if method == "GET":
            return json.dumps([]).encode()
        captured["url"] = url
        captured["body"] = body
        return json.dumps(
            {"service": "payments-api", "issue_id": "I" * 26, "pattern": "p", "explanation": "e"}
        ).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    file_path = _export_file(
        tmp_path, [{"service": "payments-api", "pattern": "p", "explanation": "e"}]
    )

    exit_code = commands.cmd_known_issues_import(_args(file_path), CONFIG)

    assert exit_code == 0
    assert captured["url"] == "https://api.example.com/known-issues"
    assert json.loads(captured["body"]) == {
        "service": "payments-api",
        "pattern": "p",
        "explanation": "e",
    }


def test_post_failure_counts_as_failed_and_exits_1(tmp_path, monkeypatch, capsys):
    def fake_request(method, url, headers=None, body=None):
        if method == "GET":
            return json.dumps([]).encode()
        raise client.BankopsError(500, "server error")

    monkeypatch.setattr(commands.client, "request", fake_request)

    file_path = _export_file(
        tmp_path, [{"service": "payments-api", "pattern": "p", "explanation": "e"}]
    )

    exit_code = commands.cmd_known_issues_import(_args(file_path), CONFIG)

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "imported=0 skipped=0 failed=1" in out
