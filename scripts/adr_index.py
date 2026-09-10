"""Regenerates the ADR table in `docs/adr/README.md` from the `# NNNN. Title`
heading of every `docs/adr/NNNN-*.md` file. Run by `task adr-index`; `ci.yml`'s
`c4` job runs it and fails if the committed file doesn't match (the same
regenerate-then-diff pattern `c4_render.py` uses for the C4 diagrams).
"""

from __future__ import annotations

import re
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / "docs" / "adr"
README = ADR_DIR / "README.md"
HEADING_RE = re.compile(r"^#\s*(\d+)\.\s*(.+)$")

HEADER = (
    "# Architecture decision records\n"
    "\n"
    "One record per decision row in [DESIGN.md](../DESIGN.md) section 2. Format: lightweight "
    "MADR. A new record is added whenever a decision changes; old ones are superseded, never "
    "edited.\n"
    "\n"
    "| # | Decision |\n"
    "|---|---|\n"
)


def _adr_files() -> list[Path]:
    return sorted(p for p in ADR_DIR.glob("*.md") if p.name != "README.md")


def build_index() -> str:
    rows = []
    for path in _adr_files():
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        match = HEADING_RE.match(first_line)
        if not match:
            raise SystemExit(f"adr_index: {path} doesn't start with '# NNNN. Title'")
        number, title = match.groups()
        rows.append((number, f"| [{number}]({path.name}) | {title} |"))
    rows.sort(key=lambda row: int(row[0]))
    return HEADER + "\n".join(row for _, row in rows) + "\n"


def main() -> int:
    README.write_text(build_index(), encoding="utf-8", newline="\n")
    print(f"rendered {README}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
