"""Patch a fault mode into the `nordwind-faults` ConfigMap, or (kafka) take
the Strimzi broker down and bring it back (stdlib only).

    python scripts/chaos_k8s.py cards-authorization timeouts
    python scripts/chaos_k8s.py cards-authorization clear
    python scripts/chaos_k8s.py kafka broker-down
    python scripts/chaos_k8s.py kafka clear

Validates the service/mode pair against `bank.faults.VALID_MODES` - the same
table `bankops chaos --estate kubernetes` validates against - before shelling
out to `kubectl`. Run by `task chaos-k8s -- <service> <mode|clear>`.

`kafka` isn't a service with a `nordwind-faults` key: its single mode,
`broker-down`, produces a real broker outage (the M7a chaos action, not a
service fault mode). Scaling the `broker` KafkaNodePool to 0 does not work:
Strimzi rejects a KRaft cluster without at least one broker replica ("At
least one KafkaNodePool with the broker role and at least one replica is
required", #78). Instead `broker-down` pauses the operator's reconciliation
of the Kafka CR (`strimzi.io/pause-reconciliation=true`), waits for the
`ReconciliationPaused` condition, and deletes the broker's StrimziPodSet -
with reconciliation paused nothing recreates it, so the broker stays gone
until `clear` removes the annotation and the operator rebuilds the pod
(ephemeral storage: the demo topics come back empty, which is the point).
The `controller` node pool (KRaft metadata quorum) is never touched.
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

KAFKA_CLUSTER = "nordwind-bank"
KAFKA_BROKER_PODSET = f"{KAFKA_CLUSTER}-broker"
KAFKA_BROKER_POOL_LABEL_SELECTOR = "strimzi.io/pool-name=broker"
PAUSE_ANNOTATION = "strimzi.io/pause-reconciliation"
_BROKER_READY_TIMEOUT = "600s"  # resume -> reconcile -> PodSet -> pod Ready took ~4 min locally
_PAUSE_TIMEOUT = "120s"


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


def _kubectl(run, *args: str) -> None:
    run(["kubectl", "-n", "bank", *args], check=True)


def pause_kafka_reconciliation(run=subprocess.run) -> None:
    _kubectl(run, "annotate", "kafka", KAFKA_CLUSTER, f"{PAUSE_ANNOTATION}=true", "--overwrite")
    _kubectl(
        run,
        "wait",
        "--for=condition=ReconciliationPaused",
        f"kafka/{KAFKA_CLUSTER}",
        f"--timeout={_PAUSE_TIMEOUT}",
    )


def resume_kafka_reconciliation(run=subprocess.run) -> None:
    _kubectl(run, "annotate", "kafka", KAFKA_CLUSTER, f"{PAUSE_ANNOTATION}-", "--overwrite")


def delete_broker_podset(run=subprocess.run) -> None:
    _kubectl(
        run, "delete", "strimzipodset", KAFKA_BROKER_PODSET, "--ignore-not-found", "--wait=true"
    )


def wait_for_broker_ready(run=subprocess.run, timeout: str = _BROKER_READY_TIMEOUT) -> None:
    # After a resume the operator needs a full reconciliation (~4 min locally)
    # before the broker PodSet exists again, and `kubectl wait` errors out on
    # a resource that is not there yet - so wait for its creation first
    # (`--for=create`, kubectl >= 1.31), then for its pod, then for Ready.
    _kubectl(
        run,
        "wait",
        "--for=create",
        f"strimzipodset/{KAFKA_BROKER_PODSET}",
        f"--timeout={timeout}",
    )
    _kubectl(
        run,
        "wait",
        "--for=jsonpath={.status.pods}=1",
        f"strimzipodset/{KAFKA_BROKER_PODSET}",
        f"--timeout={timeout}",
    )
    _kubectl(
        run,
        "wait",
        "--for=condition=Ready",
        "pod",
        "-l",
        KAFKA_BROKER_POOL_LABEL_SELECTOR,
        f"--timeout={timeout}",
    )


def kafka_broker_down(run=subprocess.run) -> None:
    pause_kafka_reconciliation(run=run)
    delete_broker_podset(run=run)


def kafka_clear(run=subprocess.run) -> None:
    resume_kafka_reconciliation(run=run)
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
