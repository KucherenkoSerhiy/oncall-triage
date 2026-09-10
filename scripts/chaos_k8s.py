"""Patch a fault mode into the `nordwind-faults` ConfigMap (stdlib only).

    python scripts/chaos_k8s.py cards-authorization timeouts
    python scripts/chaos_k8s.py cards-authorization clear

Validates the service/mode pair against `bank.faults.VALID_MODES` - the same
table `bankops chaos --estate kubernetes` validates against - before shelling
out to `kubectl`. Run by `task chaos-k8s -- <service> <mode|clear>`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bank.faults import VALID_MODES


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=sorted(VALID_MODES))
    parser.add_argument("mode", help="a valid fault mode for `service`, or 'clear'")
    args = parser.parse_args(argv)

    valid_modes = VALID_MODES[args.service]
    if args.mode == "clear":
        mode = ""
    elif args.mode in valid_modes:
        mode = args.mode
    else:
        print(
            f"error: invalid mode {args.mode!r} for {args.service}; "
            f"valid modes: {', '.join(valid_modes)} (or 'clear')",
            file=sys.stderr,
        )
        return 1

    patch_fault(args.service, mode)
    print(f"service={args.service} mode={mode or '(cleared)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
