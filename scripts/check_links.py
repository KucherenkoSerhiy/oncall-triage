"""Checks every relative Markdown link across the project's docs, and checks
the other direction too: every generated C4 view under `docs/c4/generated`
must be mentioned by name in some other document, so a diagram nobody
points at (added to `workspace.dsl`, exported, never linked) doesn't rot
unnoticed. Stdlib only, no network calls - an offline gate, like
`scripts/adr_index.py` and `scripts/c4_drift.py`. Run by `ci.yml`'s
`python` job and `task docs-check` (see docs/specs/m9e).

    python scripts/check_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_GLOBS = ("README.md", "docs/**/*.md", "infra/README.md", "bank/**/README.md")

# Inline links and images: [text](target) / ![alt](target), with an
# optional " title" after the target. Reference-style links aren't used
# anywhere in this repo's docs, so they're out of scope.
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")

GENERATED_C4_DIR = Path("docs") / "c4" / "generated"


def find_doc_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in DOC_GLOBS:
        files.update(root.glob(pattern))
    return sorted(files)


def _is_external(target: str) -> bool:
    return target.startswith("//") or bool(_SCHEME_RE.match(target))


def find_broken_links(root: Path, doc_files: list[Path]) -> list[str]:
    """Relative link targets that don't resolve to a file or directory on disk."""
    errors = []
    for doc in doc_files:
        text = doc.read_text(encoding="utf-8")
        for match in _LINK_RE.finditer(text):
            target = match.group(1)
            if not target or target.startswith("#") or _is_external(target):
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            resolved = (doc.parent / path_part).resolve()
            if not resolved.exists():
                errors.append(f"{doc.relative_to(root)}: broken link -> {target}")
    return errors


def _view_key(path: Path) -> str:
    key = path.stem
    prefix = "structurizr-"
    return key[len(prefix) :] if key.startswith(prefix) else key


def find_orphaned_c4_views(root: Path, doc_files: list[Path]) -> list[str]:
    """Every file in docs/c4/generated (other than its own README.md index)
    must be mentioned by name somewhere outside that directory - otherwise a
    view exists that no document ever points a reader at."""
    generated_dir = root / GENERATED_C4_DIR
    if not generated_dir.is_dir():
        return []

    generated_readme = generated_dir / "README.md"
    corpus = "\n".join(
        doc.read_text(encoding="utf-8") for doc in doc_files if doc != generated_readme
    )

    errors = []
    for path in sorted(generated_dir.iterdir()):
        if path.is_dir() or path.name == "README.md":
            continue
        key = _view_key(path)
        if key not in corpus:
            errors.append(
                f"{(GENERATED_C4_DIR / path.name).as_posix()}: view '{key}' isn't "
                "mentioned in any other document"
            )
    return errors


def check(root: Path) -> list[str]:
    doc_files = find_doc_files(root)
    return find_broken_links(root, doc_files) + find_orphaned_c4_views(root, doc_files)


def main() -> int:
    errors = check(REPO_ROOT)
    if errors:
        for error in errors:
            print(f"::error::{error}")
        print(f"check_links: {len(errors)} failure(s)")
        return 1
    print("check_links: all relative links resolve, no orphaned C4 views")
    return 0


if __name__ == "__main__":
    sys.exit(main())
