"""CLI entry point for link-tracer."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import click
import structlog
from dotenv import dotenv_values, find_dotenv

from link_tracer.api import trace_links
from link_tracer.logging import configure_debug_logging, get_console
from link_tracer.models import TraceOptions

logger = structlog.get_logger(__name__)


def resolve_vault_root(cli_value: Path | None) -> Path:
    """Resolve vault root directory with precedence: CLI > .vault > env var."""
    if cli_value:
        resolved = cli_value if cli_value.is_absolute() else (Path.cwd() / cli_value).resolve()
        if not resolved.exists():
            raise click.UsageError(f"Vault root directory does not exist: {resolved}")
        return resolved

    vault_path = find_dotenv(filename=".vault", usecwd=True)
    if vault_path:
        values = dotenv_values(vault_path)
        vault_root_value = values.get("VAULT_ROOT")
        if vault_root_value:
            vault_file = Path(vault_path)
            path = Path(vault_root_value)
            resolved = path if path.is_absolute() else (vault_file.parent / path).resolve()
            if not resolved.exists():
                raise click.UsageError(f"Vault root directory does not exist: {resolved}")
            return resolved

    env_value = os.environ.get("VAULT_ROOT")
    if env_value:
        path = Path(env_value)
        resolved = path if path.is_absolute() else (Path.cwd() / path).resolve()
        if not resolved.exists():
            raise click.UsageError(f"Vault root directory does not exist: {resolved}")
        return resolved

    raise click.UsageError(
        "No vault root directory provided. "
        "Use --vault-root, set VAULT_ROOT env var, or create a .vault file."
    )


@click.command()
@click.argument("note", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Vault root directory (overrides VAULT_ROOT env and .vault file)",
)
@click.option("--follow-chain", is_flag=True, help="Follow links recursively")
@click.option("--max-depth", type=int, default=None, help="Traversal depth limit")
@click.option("--debug", is_flag=True, help="Enable debug-level structured logging to stderr")
@click.option("--verbose", is_flag=True, help="Enable verbose console output")
def main(
    note: Path,
    vault_root: Path | None,
    follow_chain: bool,
    max_depth: int | None,
    debug: bool,
    verbose: bool,
) -> int:
    """Trace Obsidian note links to filesystem sources."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "Starting link tracer", note=str(note), vault_root=str(vault_root) if vault_root else None
    )
    vault_root = resolve_vault_root(vault_root)
    options = TraceOptions(follow_chain=follow_chain, max_depth=max_depth)
    logger.info("Tracing links", note=str(note))
    response = trace_links(note_path=note, vault_root=vault_root, options=options)
    click.echo(json.dumps(asdict(response), indent=2))
    console.print("Link tracing complete")
    logger.info("Link tracing complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
