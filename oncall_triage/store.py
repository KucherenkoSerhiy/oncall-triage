"""Known-issues store: a local JSON file of previously-explained log errors."""

import json
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_STORE_PATH = _REPO_ROOT / "known_issues.json"


def _store_path() -> Path:
    configured = os.environ.get("TRIAGE_STORE_PATH")
    return Path(configured) if configured else _DEFAULT_STORE_PATH


def _load(path: Path | None = None) -> dict:
    path = path or _store_path()
    if not path.exists():
        return {"issues": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict, path: Path | None = None) -> None:
    # Atomic replace: a crash mid-write must never leave a half-written
    # store — the whole known-issues memory would be unreadable JSON.
    path = path or _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def find_known(error_text: str, path: Path | None = None) -> dict | None:
    """Return the matching issue record if error_text contains a known pattern."""
    data = _load(path)
    error_lower = error_text.lower()
    for issue in data.get("issues", []):
        if issue["pattern"].lower() in error_lower:
            return issue
    return None


def add_known(error_pattern: str, explanation: str, path: Path | None = None) -> dict:
    """Persist a new known-issue pattern and explanation."""
    data = _load(path)
    record = {"pattern": error_pattern, "explanation": explanation}
    data.setdefault("issues", []).append(record)
    _save(data, path)
    return record
