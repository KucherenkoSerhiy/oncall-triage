"""Substitutes the `__FORWARDER_URL__` placeholder in the kube-prometheus-stack
Alertmanager values (`deploy/helm/values/kube-prometheus-stack.yaml`).

Upstream `kube-prometheus-stack` values can't read this repo's own
`nordwind-bank` chart values, so the Alertmanager receiver's webhook URL is
injected at install time instead: M6b's `task estate-up` runs this script
before `helm upgrade` to substitute the real `bank/azure/alert_forwarder`
function URL. An empty/missing URL substitutes a dummy local address so the
rendered values stay a valid `webhook_configs` list either way.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PLACEHOLDER = "__FORWARDER_URL__"
DUMMY_URL = "http://127.0.0.1:9/"


def render(values_text: str, forwarder_url: str) -> str:
    return values_text.replace(PLACEHOLDER, forwarder_url or DUMMY_URL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values_file", type=Path, help="Path to kube-prometheus-stack.yaml")
    parser.add_argument("--forwarder-url", default="", help="alert_forwarder function URL")
    args = parser.parse_args(argv)

    sys.stdout.write(render(args.values_file.read_text(), args.forwarder_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
