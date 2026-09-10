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
    parser.add_argument(
        "--alerts-queue-url", default=None, help="Alerts SQS queue URL (bankops replay-dlq)"
    )
    parser.add_argument(
        "--alerts-dlq-url",
        default=None,
        help="Alerts SQS dead-letter queue URL (bankops replay-dlq)",
    )

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

    # "known-issues" groups the M9b additions (import) with a "list" alias
    # of the "known" command above, so `bankops known-issues list|import`
    # both live under one namespace as docs/specs/m9b-known-issues-export-
    # and-dlq.md names them; `bankops known` is untouched.
    known_issues = subparsers.add_parser("known-issues", help="List or import known issues")
    known_issues_sub = known_issues.add_subparsers(dest="known_issues_command", required=True)

    known_issues_list = known_issues_sub.add_parser("list", help="List known issues")
    known_issues_list.add_argument("--service", default=None)

    known_issues_import = known_issues_sub.add_parser(
        "import", help="Re-teach known issues from a known-issues-export JSON file"
    )
    known_issues_import.add_argument("file")
    known_issues_import.add_argument("--dry-run", action="store_true")

    _replay_dlq_help = (
        "Move messages from the alerts DLQ back to the alerts queue "
        "(talks to SQS directly - needs AWS credentials, not just the console API token)"
    )
    replay_dlq = subparsers.add_parser(
        "replay-dlq", help=_replay_dlq_help, description=_replay_dlq_help
    )
    replay_dlq.add_argument("--max", type=int, default=10)
    replay_dlq.add_argument("--yes", action="store_true", help="Actually move messages")

    chaos = subparsers.add_parser("chaos", help="Inject, clear, or view a chaos fault")
    chaos.add_argument(
        "service", nargs="?", default=None, help="payments | ledger | auth | customer-notifications"
    )
    chaos.add_argument("--mode", default=None)
    chaos.add_argument("--minutes", type=int, default=5)
    chaos.add_argument("--clear", action="store_true")
    chaos.add_argument("--status", action="store_true")
    chaos.add_argument(
        "--estate",
        default="aws",
        choices=["aws", "kubernetes"],
        help="aws: console API route (default); kubernetes: kubectl patch nordwind-faults",
    )

    return parser


def _config_from(args: argparse.Namespace) -> Config:
    return Config(
        api=args.api or os.environ.get("BANKOPS_API", ""),
        hmac_secret=args.hmac_secret or os.environ.get("BANKOPS_HMAC_SECRET", ""),
        token=args.token or os.environ.get("BANKOPS_TOKEN", ""),
        alerts_queue_url=args.alerts_queue_url or os.environ.get("BANKOPS_ALERTS_QUEUE_URL", ""),
        alerts_dlq_url=args.alerts_dlq_url or os.environ.get("BANKOPS_ALERTS_DLQ_URL", ""),
    )


_HANDLERS = {
    "fire": commands.cmd_fire,
    "tail": commands.cmd_tail,
    "teach": commands.cmd_teach,
    "known": commands.cmd_known,
    "chaos": commands.cmd_chaos,
    "replay-dlq": commands.cmd_replay_dlq,
}

_KNOWN_ISSUES_HANDLERS = {
    "list": commands.cmd_known,
    "import": commands.cmd_known_issues_import,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = _config_from(args)
    if args.command == "known-issues":
        return _KNOWN_ISSUES_HANDLERS[args.known_issues_command](args, config)
    return _HANDLERS[args.command](args, config)


if __name__ == "__main__":
    sys.exit(main())
