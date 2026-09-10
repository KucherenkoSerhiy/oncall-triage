"""Patch a fault mode into the `nordwind-faults` ConfigMap, or (kafka) scale
the Strimzi `KafkaNodePool` (stdlib only).

    python scripts/chaos_k8s.py cards-authorization timeouts
    python scripts/chaos_k8s.py cards-authorization clear
    python scripts/chaos_k8s.py kafka broker-down
    python scripts/chaos_k8s.py kafka clear

Validates the service/mode pair against `bank.faults.VALID_MODES` - the same
table `bankops chaos --estate kubernetes` validates against - before shelling
out to `kubectl`. Run by `task chaos-k8s -- <service> <mode|clear>`.

`kafka` isn't a service with a `nordwind-faults` key: its single mode,
`broker-down`, scales the `broker` `KafkaNodePool` to 0 replicas instead
(the M7a chaos action, not a service fault mode); `clear` scales it back to
1 and waits for the broker pod to become Ready. The `controller` node pool
(KRaft metadata quorum) is never touched - Strimzi refuses to reconcile a
Kafka cluster whose node pools sum to 0 replicas across the board, so a
combined controller+broker pool can't be scaled to 0 to produce a broker
outage; see `deploy/helm/nordwind-bank/templates/kafka/kafkanodepool.yaml`.
`cli/bankops/commands.py` imports `kafka_broker_down`/`kafka_clear` from
here directly so `bankops chaos --estate kubernetes kafka` goes through the
same code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bank.faults import VALID_MODES

KAFKA_NODE_POOL = "broker"
KAFKA_BROKER_POOL_LABEL_SELECTOR = "strimzi.io/pool-name=broker"
_BROKER_READY_TIMEOUT = "180s"


def patch_fault(service: str, mode: str, run=subprocess.run) -> None:
    patch = json.dumps({"data": {service: mode}})
    run(
        [
            "kubectl",
            "-n",
            "bank",
            "patch",
            "configmap",
            "nordwind-faults",
            "--type",
            "merge",
            "-p",
            patch,
        ],
        check=True,
    )


def scale_kafka_node_pool(replicas: int, run=subprocess.run) -> None:
    patch = json.dumps({"spec": {"replicas": replicas}})
    run(
        [
            "kubectl",
            "-n",
            "bank",
            "patch",
            "kafkanodepool",
            KAFKA_NODE_POOL,
            "--type",
            "merge",
            "-p",
            patch,
        ],
        check=True,
    )


def wait_for_broker_ready(run=subprocess.run, timeout: str = _BROKER_READY_TIMEOUT) -> None:
    run(
        [
            "kubectl",
            "-n",
            "bank",
            "wait",
            "--for=condition=Ready",
            "pod",
            "-l",
            KAFKA_BROKER_POOL_LABEL_SELECTOR,
            f"--timeout={timeout}",
        ],
        check=True,
    )


def kafka_broker_down(run=subprocess.run) -> None:
    scale_kafka_node_pool(0, run=run)


def kafka_clear(run=subprocess.run) -> None:
    scale_kafka_node_pool(1, run=run)
    wait_for_broker_ready(run=run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=sorted(VALID_MODES))
    parser.add_argument("mode", help="a valid fault mode for `service`, or 'clear'")
    args = parser.parse_args(argv)

    valid_modes = VALID_MODES[args.service]
    if args.mode != "clear" and args.mode not in valid_modes:
        print(
            f"error: invalid mode {args.mode!r} for {args.service}; "
            f"valid modes: {', '.join(valid_modes)} (or 'clear')",
            file=sys.stderr,
        )
        return 1

    if args.service == "kafka":
        if args.mode == "clear":
            kafka_clear()
        else:
            kafka_broker_down()
        print(f"service=kafka mode={args.mode}")
        return 0

    mode = "" if args.mode == "clear" else args.mode
    patch_fault(args.service, mode)
    print(f"service={args.service} mode={mode or '(cleared)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
