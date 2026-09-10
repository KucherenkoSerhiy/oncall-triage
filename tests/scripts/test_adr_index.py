from __future__ import annotations

from pathlib import Path

from scripts import adr_index


def test_build_index_sorts_and_formats_rows(monkeypatch, tmp_path: Path):
    (tmp_path / "0002-second.md").write_text("# 0002. Second decision\n", encoding="utf-8")
    (tmp_path / "0001-first.md").write_text("# 0001. First decision\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("stale content", encoding="utf-8")
    monkeypatch.setattr(adr_index, "ADR_DIR", tmp_path)

    index = adr_index.build_index()

    first = index.index("[0001]")
    second = index.index("[0002]")
    assert first < second
    assert "| [0001](0001-first.md) | First decision |" in index
    assert "| [0002](0002-second.md) | Second decision |" in index


def test_build_index_rejects_a_file_without_a_numbered_heading(monkeypatch, tmp_path: Path):
    (tmp_path / "0001-bad.md").write_text("Not a heading\n", encoding="utf-8")
    monkeypatch.setattr(adr_index, "ADR_DIR", tmp_path)

    try:
        adr_index.build_index()
    except SystemExit:
        pass
    else:
        raise AssertionError("expected SystemExit")
