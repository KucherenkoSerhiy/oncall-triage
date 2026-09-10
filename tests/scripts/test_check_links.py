from __future__ import annotations

from pathlib import Path

from scripts import check_links


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_check_passes_on_a_clean_tree(tmp_path: Path):
    _write(tmp_path / "README.md", "See [docs](docs/guide.md) and the [repo](.).\n")
    _write(tmp_path / "docs" / "guide.md", "# Guide\n")

    assert check_links.check(tmp_path) == []


def test_broken_relative_link_is_reported(tmp_path: Path):
    _write(tmp_path / "README.md", "See [missing](docs/missing.md).\n")

    errors = check_links.check(tmp_path)

    assert len(errors) == 1
    assert "README.md" in errors[0]
    assert "docs/missing.md" in errors[0]


def test_external_and_anchor_links_are_ignored(tmp_path: Path):
    _write(
        tmp_path / "README.md",
        "[external](https://example.com/x) [anchor](#section) [mailto](mailto:a@b.com)\n",
    )

    assert check_links.check(tmp_path) == []


def test_link_with_fragment_resolves_against_the_file_not_the_fragment(tmp_path: Path):
    _write(tmp_path / "README.md", "[section](docs/guide.md#usage)\n")
    _write(tmp_path / "docs" / "guide.md", "# Guide\n")

    assert check_links.check(tmp_path) == []


def test_image_links_are_checked_like_regular_links(tmp_path: Path):
    _write(tmp_path / "README.md", "![diagram](docs/missing.png)\n")

    errors = check_links.check(tmp_path)

    assert len(errors) == 1
    assert "docs/missing.png" in errors[0]


def test_bank_and_infra_readmes_are_walked(tmp_path: Path):
    _write(tmp_path / "infra" / "README.md", "[gone](nope.md)\n")
    _write(tmp_path / "bank" / "aws" / "README.md", "[gone](nope.md)\n")

    errors = check_links.check(tmp_path)

    assert len(errors) == 2


def test_orphaned_c4_view_is_reported(tmp_path: Path):
    _write(tmp_path / "README.md", "nothing about diagrams here\n")
    _write(
        tmp_path / "docs" / "c4" / "generated" / "structurizr-context.mmd",
        "graph LR\n  a-->b\n",
    )

    errors = check_links.check(tmp_path)

    assert len(errors) == 1
    assert "structurizr-context.mmd" in errors[0]
    assert "context" in errors[0]


def test_c4_view_referenced_by_name_elsewhere_is_not_orphaned(tmp_path: Path):
    _write(tmp_path / "docs" / "c4" / "README.md", "See the context view.\n")
    _write(
        tmp_path / "docs" / "c4" / "generated" / "structurizr-context.mmd",
        "graph LR\n  a-->b\n",
    )

    assert check_links.check(tmp_path) == []


def test_generated_readme_embedding_the_view_does_not_count_as_a_reference(tmp_path: Path):
    # The wrapper README.md inlines every .mmd file's raw content - that's
    # not a document *pointing at* the view, so it must not satisfy the check.
    _write(
        tmp_path / "docs" / "c4" / "generated" / "structurizr-context.mmd",
        "graph LR\n  a-->b\n",
    )
    _write(
        tmp_path / "docs" / "c4" / "generated" / "README.md",
        "## context\n\n```mermaid\ngraph LR\n  a-->b\n```\n",
    )

    errors = check_links.check(tmp_path)

    assert len(errors) == 1
    assert "structurizr-context.mmd" in errors[0]


def test_missing_generated_dir_is_not_an_error(tmp_path: Path):
    _write(tmp_path / "README.md", "# Nothing here\n")

    assert check_links.check(tmp_path) == []
