"""CLI entry point for link-tracer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from link_tracer.api import trace_links
from link_tracer.models import TraceOptions


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="link-tracer",
        description="Trace Obsidian note links to filesystem sources.",
    )
    parser.add_argument("note", type=Path, help="Path to the starting note.")
    parser.add_argument("--vault", type=Path, required=True, help="Vault root path.")
    parser.add_argument(
        "--follow-chain",
        action="store_true",
        help="Follow links recursively (stub).",
    )
    parser.add_argument("--max-depth", type=int, default=None, help="Traversal depth limit.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and print JSON output."""
    parser = build_parser()
    args = parser.parse_args(argv)
    options = TraceOptions(follow_chain=args.follow_chain, max_depth=args.max_depth)
    payload = trace_links(note_path=args.note, vault_root=args.vault, options=options)

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
