"""Fault-mode file reader shared by the three Kubernetes bank services.

Each service's Deployment mounts its own key of the ``nordwind-faults``
ConfigMap at ``/etc/nordwind/fault`` (M6a Helm chart, one file per pod via
``items`` + ``path: fault``). ``bankops chaos --estate kubernetes`` (M6b)
patches the ConfigMap key; this reader re-reads the file at most once every
``ttl`` seconds so a busy ticker loop doesn't stat() the file every tick.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from pathlib import Path

logger = logging.getLogger(__name__)


class FaultFile:
    def __init__(
        self,
        path: str = "/etc/nordwind/fault",
        ttl: float = 5,
        valid_modes: Iterable[str] = (),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._path = Path(path)
        self._ttl = ttl
        self._valid_modes = frozenset(valid_modes)
        self._clock = clock
        self._cached_mode: str | None = None
        self._checked_at: float | None = None
        self._warned_modes: set[str] = set()

    def current(self) -> str | None:
        """Return the active fault mode, or ``None`` for normal operation."""
        now = self._clock()
        if self._checked_at is not None and now - self._checked_at < self._ttl:
            return self._cached_mode

        self._checked_at = now
        try:
            raw = self._path.read_text().strip()
        except OSError:
            raw = ""

        if not raw:
            self._cached_mode = None
        elif self._valid_modes and raw not in self._valid_modes:
            if raw not in self._warned_modes:
                logger.warning("unknown fault mode %r on %s; running normal", raw, self._path)
                self._warned_modes.add(raw)
            self._cached_mode = None
        else:
            self._cached_mode = raw

        return self._cached_mode
