"""``python -m cli.bankops`` entry point."""

from __future__ import annotations

import argparse
import os
import sys

from cli.bankops import commands
from cli.bankops.commands import Config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bankops")
    parser.add_argument("--api", default=None, help="Console/ingest API base URL")
    parser.add_argument("--hmac-secret", default=None, help="Ingest HMAC secret")
    parser.add_argument("--token", default=None, help="Console API bearer token")

    subparsers = parser.add_subparsers(dest="command", required=True)

    fire = subparsers.add_parser("fire", help="Fire a synthetic alert")
    fire.add_argument("--service", required=True)
    fire.add_argument("--alert", required=True)
    fire.add_argument("--severity", default="sev3", choices=["sev1", "sev2", "sev3", "sev4"])
    fire.add_argument("--title", default=None)
    fire.add_argument("--description", default=None)
    fire.add_argument("--estate", default="aws", choices=["aws", "azure", "kubernetes"])
    fire.add_argument("--label", action="append", default=[], metavar="k=v")
    fire.add_argument("--log", action="append", default=[], metavar="LINE")

    tail = subparsers.add_parser("tail", help="Tail recent alerts")
    tail.add_argument("--limit", type=int, default=50)
    tail.add_argument("--watch", action="store_true")
    tail.add_argument("--interval", type=int, default=10)

    teach = subparsers.add_parser("teach", help="Add a known issue")
    teach.add_argument("--service", required=True)
    teach.add_argument("--pattern", required=True)
    teach.add_argument("--explanation", required=True)

    known = subparsers.add_parser("known", help="List known issues")
    known.add_argument("--service", default=None)

    chaos = subparsers.add_parser("chaos", help="Inject, clear, or view a chaos fault")
    chaos.add_argument("service", nargs="?", default=None, help="payments | ledger | auth")
    chaos.add_argument("--mode", default=None)
    chaos.add_argument("--minutes", type=int, default=5)
    chaos.add_argument("--clear", action="store_true")
    chaos.add_argument("--status", action="store_true")

    return parser


def _config_from(args: argparse.Namespace) -> Config:
    return Config(
        api=args.api or os.environ.get("BANKOPS_API", ""),
        hmac_secret=args.hmac_secret or os.environ.get("BANKOPS_HMAC_SECRET", ""),
        token=args.token or os.environ.get("BANKOPS_TOKEN", ""),
    )


_HANDLERS = {
    "fire": commands.cmd_fire,
    "tail": commands.cmd_tail,
    "teach": commands.cmd_teach,
    "known": commands.cmd_known,
    "chaos": commands.cmd_chaos,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = _config_from(args)
    return _HANDLERS[args.command](args, config)


if __name__ == "__main__":
    sys.exit(main())
