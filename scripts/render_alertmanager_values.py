"""Substitutes the `__FORWARDER_URL__` placeholder in the kube-prometheus-stack
Alertmanager values (`deploy/helm/values/kube-prometheus-stack.yaml`), and
(M7b) swaps its Alertmanager routing between the two-route estate (Kafka
enabled) and the M6 estate (everything to route B).

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

# The `route:`/`receivers:` block in kube-prometheus-stack.yaml between these
# two marker comments is the kafka.enabled=true routing (route A by default,
# route B only for Kafka's own alerts). `--no-kafka` swaps it for the M6
# routing below - everything to route B, no Kafka receiver at all - since
# there's no alerts-bridge to webhook to when the chart renders without Kafka.
_ROUTE_BLOCK_START = "    # __ROUTE_KAFKA_BLOCK_START__\n"
_ROUTE_BLOCK_END = "    # __ROUTE_KAFKA_BLOCK_END__\n"

_NO_KAFKA_ROUTE_BLOCK = """    route:
      receiver: route-b-forwarder
      group_by: ["alertname", "service"]
      group_wait: 10s
      group_interval: 30s
      repeat_interval: 1h
    receivers:
      - name: route-b-forwarder
        webhook_configs:
          - url: "__FORWARDER_URL__"
            send_resolved: true
"""


def render(
    values_text: str, forwarder_url: str, cluster_label: str = "", kafka: bool = True
) -> str:
    """Substitute the forwarder URL, the per-run `cluster` external label,
    and (if `kafka` is False) the Alertmanager routing block.

    The cluster label rides on every alert Prometheus raises, so two demo
    runs inside ingest's 30-minute dedup window get different fingerprints
    instead of the second one being silently absorbed (#71) - the same
    failure the smoke probe had (#38)."""
    text = values_text
    if kafka:
        # The markers exist only to bracket the block for --no-kafka; strip
        # them so they never show up in a real rendered values file.
        text = text.replace(_ROUTE_BLOCK_START, "").replace(_ROUTE_BLOCK_END, "")
    else:
        start = text.index(_ROUTE_BLOCK_START)
        end = text.index(_ROUTE_BLOCK_END, start) + len(_ROUTE_BLOCK_END)
        text = text[:start] + _NO_KAFKA_ROUTE_BLOCK + text[end:]
    return text.replace(PLACEHOLDER, forwarder_url or DUMMY_URL).replace(
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
    parser.add_argument(
        "--kafka",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="render the route-A/route-B Kafka routing (default); --no-kafka renders the M6 "
        "routing (everything to route B), matching --set kafka.enabled=false",
    )
    args = parser.parse_args(argv)

    sys.stdout.write(
        render(args.values_file.read_text(), args.forwarder_url, args.cluster_label, args.kafka)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
