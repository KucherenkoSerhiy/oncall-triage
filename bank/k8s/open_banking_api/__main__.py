"""Entrypoint: `python -m open_banking_api` (image) /
`python -m bank.k8s.open_banking_api` (repo)."""

from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry

try:
    from _shared.server import run
    from _shared.ticker import Ticker
except ImportError:
    from bank.k8s._shared.server import run
    from bank.k8s._shared.ticker import Ticker

from .service import OpenBankingApiService


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()
    service = OpenBankingApiService(registry)
    ticker = Ticker(service.work)
    ticker.start()
    run(service.work, registry).serve_forever()


if __name__ == "__main__":
    main()
