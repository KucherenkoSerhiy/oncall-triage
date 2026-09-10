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
CLUSTER_PLACEHOLDER = "__CLUSTER_LABEL__"
DUMMY_URL = "http://127.0.0.1:9/"
DEFAULT_CLUSTER_LABEL = "kind-local"


def render(values_text: str, forwarder_url: str, cluster_label: str = "") -> str:
    """Substitute the forwarder URL and the per-run `cluster` external label.

    The label rides on every alert Prometheus raises, so two demo runs inside
    ingest's 30-minute dedup window get different fingerprints instead of the
    second one being silently absorbed (#71) - the same failure the smoke
    probe had (#38)."""
    return values_text.replace(PLACEHOLDER, forwarder_url or DUMMY_URL).replace(
        CLUSTER_PLACEHOLDER, cluster_label or DEFAULT_CLUSTER_LABEL
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values_file", type=Path, help="Path to kube-prometheus-stack.yaml")
    parser.add_argument("--forwarder-url", default="", help="alert_forwarder function URL")
    parser.add_argument(
        "--cluster-label",
        default="",
        help="value of the `cluster` external label (unique per demo run; default kind-local)",
    )
    args = parser.parse_args(argv)

    sys.stdout.write(render(args.values_file.read_text(), args.forwarder_url, args.cluster_label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
