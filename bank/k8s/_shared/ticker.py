"""Background thread that drives a service's `/work` function once a second.

`fraud_scoring`'s `crashloop` fault calls `sys.exit(1)` from inside the work
function so the pod's Deployment restarts it (CrashLoopBackOff). Raising
`SystemExit` on a background thread only ends that thread, not the process,
so it is turned into a real process exit here instead.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class Ticker:
    def __init__(self, work: Callable[[], object], interval: float = 1.0) -> None:
        self._work = work
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._work()
            except SystemExit as exc:
                logger.info("ticker work raised SystemExit(%r); exiting process", exc.code)
                os._exit(exc.code if isinstance(exc.code, int) else 1)
            except Exception:
                logger.exception("ticker work failed")
