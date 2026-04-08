"""CLI entry point for link-tracer."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import click
import structlog
from dotenv import dotenv_values, find_dotenv

from link_tracer import resolve_links, build_graph, scan_vault
from link_tracer.logging import configure_debug_logging, get_console
from link_tracer.models import ResolveOptions

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


def emit_json_output(payload: str, output: Path | None) -> None:
    """Emit JSON payload to stdout or a target file.

    Args:
        payload: Serialized JSON payload.
        output: Optional output file path.
    """
    if output is None:
        click.echo(payload)
        return

    try:
        output.write_text(f"{payload}\n", encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Could not write output file {output}: {exc}") from exc


@click.group()
def main() -> None:
    """Trace Obsidian note links to filesystem sources."""


@main.command("note")
@click.argument("note", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Vault root directory (overrides VAULT_ROOT env and .vault file)",
)
@click.option(
    "--depth",
    type=int,
    default=1,
    help="Traversal depth (0=source only, 1=direct links, 2+=recursive)",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Write JSON output to file instead of stdout",
)
@click.option("--debug", is_flag=True, help="Enable debug-level structured logging to stderr")
@click.option("--verbose", is_flag=True, help="Enable verbose console output")
def trace_note(
    note: Path,
    vault_root: Path | None,
    depth: int,
    output: Path | None,
    debug: bool,
    verbose: bool,
) -> int:
    """Trace links for a single note."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "Starting link tracer", note=str(note), vault_root=str(vault_root) if vault_root else None
    )
    vault_root = resolve_vault_root(vault_root)
    options = ResolveOptions(depth=depth)
    logger.info("Tracing links", note=str(note))
    vault_index = scan_vault(vault_root)
    vault_graph = build_graph(vault_index=vault_index)
    source_note, graph = resolve_links(note_path=note, vault_graph=vault_graph, vault_index=vault_index, options=options)
    payload = json.dumps({"source_note": source_note, **asdict(graph)}, indent=2)
    emit_json_output(payload, output)
    console.print("Link tracing complete")
    logger.info("Link tracing complete")
    return 0


@main.command("graph")
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Vault root directory (overrides VAULT_ROOT env and .vault file)",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Write JSON output to file instead of stdout",
)
@click.option("--debug", is_flag=True, help="Enable debug-level structured logging to stderr")
@click.option("--verbose", is_flag=True, help="Enable verbose console output")
def trace_graph(vault_root: Path | None, output: Path | None, debug: bool, verbose: bool) -> int:
    """Trace links for every note in the vault."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug("Starting vault link tracer", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("Tracing vault links", vault_root=str(vault_root))
    vault_index = scan_vault(vault_root)
    response = build_graph(vault_index=vault_index)
    payload = json.dumps(asdict(response), indent=2)
    emit_json_output(payload, output)
    console.print("Vault link tracing complete")
    logger.info("Vault link tracing complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
