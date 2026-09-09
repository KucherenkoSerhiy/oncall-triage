"""Entrypoint: `python -m cards_authorization` (image) /
`python -m bank.k8s.cards_authorization` (repo)."""

from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry

try:
    from _shared.server import run
    from _shared.ticker import Ticker
except ImportError:
    from bank.k8s._shared.server import run
    from bank.k8s._shared.ticker import Ticker

from .service import CardsAuthorizationService


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()
    service = CardsAuthorizationService(registry)
    ticker = Ticker(service.work)
    ticker.start()
    run(service.work, registry).serve_forever()


if __name__ == "__main__":
    main()
