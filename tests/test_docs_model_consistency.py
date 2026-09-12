"""The model named in the live documentation must be the one the code uses.

A reviewer found ARCHITECTURE.md still naming the phase-1 Gemini model while
README.md said Claude Haiku 4.5. The default lives in one place
(`oncall_triage.model._DEFAULT_MODEL`); the documents that describe the
current system must agree with it, and may name the phase-1 model only on
lines that say it is history.
"""

from pathlib import Path

from oncall_triage.model import _DEFAULT_MODEL

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_DOCS = ["README.md", "ARCHITECTURE.md", "docs/DESIGN.md", "infra/README.md"]
PHASE_ONE_MODEL = "gemini-3.5-flash-lite"
HISTORY_MARKERS = ("phase 1", "Phase 1", "phase-1", "historical", "was ", "ran on", "used ")


def _lines(path: str) -> list[str]:
    return (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()


def test_architecture_names_the_default_model():
    text = "\n".join(_lines("ARCHITECTURE.md"))
    assert _DEFAULT_MODEL in text, "ARCHITECTURE.md must name the code's default model id"


def test_live_docs_only_mention_the_phase_one_model_as_history():
    offenders = []
    for path in LIVE_DOCS:
        for number, line in enumerate(_lines(path), start=1):
            names_current = "claude" in line.lower()
            if (
                PHASE_ONE_MODEL in line
                and not names_current
                and not any(marker in line for marker in HISTORY_MARKERS)
            ):
                offenders.append(f"{path}:{number}: {line.strip()[:100]}")
    assert not offenders, "phase-1 model named as if current:\n" + "\n".join(offenders)
