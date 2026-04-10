"""CLI entry point for vault-net."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import click
import structlog

from vault_net import (
    VaultRegistry,
    build_note_ego_graph,
    build_vault_digraph,
    scan_vault,
)
from vault_net.logging import configure_debug_logging, get_console
from vault_net.models import VaultGraph, VaultGraphMetadata
from vault_net.transforms import build_adjacency_list, build_layered_repr, build_vault_edge_list
from vault_net.utils import collapse_vault_file_json

logger = structlog.get_logger(__name__)


def resolve_vault_root(cli_value: Path | None) -> Path:
    """Resolve vault root directory with precedence: CLI > env var."""
    if cli_value:
        resolved = cli_value if cli_value.is_absolute() else (Path.cwd() / cli_value).resolve()
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
        "Use --vault-root or set the VAULT_ROOT environment variable."
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


def _serialize_edge_list(
    graph: VaultGraph,
    vault_registry: VaultRegistry,
) -> dict[str, object]:
    """Serialize graph edges to an edge_list payload."""
    edges = build_vault_edge_list(graph, vault_registry)
    return {
        "vault_root": str(graph.vault_root),
        "metadata": {"edge_count": len(edges)},
        "edges": [[asdict(source), asdict(target)] for source, target in edges],
    }


def _serialize_adjacency_list(
    graph: VaultGraph,
    vault_registry: VaultRegistry,
) -> dict[str, list[object]]:
    """Serialize graph adjacency as source slug -> target VaultFile list."""
    adjacency = build_adjacency_list(graph, vault_registry)
    return {
        source_slug: [asdict(target_file) for target_file in target_files]
        for source_slug, target_files in adjacency.items()
    }


@main.command("note-graph")
@click.argument("slug", type=str)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Vault root directory (overrides VAULT_ROOT env and .vault file)",
)
@click.option(
    "-d",
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
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["edge_list", "adjacency_list", "layered"], case_sensitive=False),
    default="edge_list",
    help="Output graph representation",
)
@click.option(
    "-e",
    "--exclude-dir",
    "extra_exclude_dir",
    multiple=True,
    metavar="DIR",
    help="Additional directory name to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude-dir entries",
)
def note_graph(
    slug: str,
    vault_root: Path | None,
    depth: int,
    output: Path | None,
    debug: bool,
    verbose: bool,
    fmt: str,
    extra_exclude_dir: tuple[str, ...],
    no_default_excludes: bool,
) -> int:
    """Trace links for a single note."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "Starting link tracer", slug=slug, vault_root=str(vault_root) if vault_root else None
    )
    vault_root = resolve_vault_root(vault_root)
    logger.info("Tracing links", slug=slug)
    vault_index = scan_vault(
        vault_root, extra_exclude_dir=extra_exclude_dir, no_default_excludes=no_default_excludes
    )
    vault_registry = VaultRegistry(vault_index)
    vault_graph = build_vault_digraph(vault_index=vault_index)

    try:
        ego_graph = build_note_ego_graph(slug, vault_graph.digraph, depth=depth)
    except KeyError as exc:
        raise click.UsageError(f"Unknown slug '{slug}'.") from exc

    ego_vault_graph = VaultGraph(
        vault_root=vault_root,
        metadata=VaultGraphMetadata(edge_count=ego_graph.number_of_edges()),
        digraph=ego_graph,
    )

    if fmt == "layered":
        payload = json.dumps(asdict(build_layered_repr(slug, ego_vault_graph)), indent=2)
    elif fmt == "adjacency_list":
        payload = json.dumps(_serialize_adjacency_list(ego_vault_graph, vault_registry), indent=2)
    else:
        payload = json.dumps(_serialize_edge_list(ego_vault_graph, vault_registry), indent=2)

    payload = collapse_vault_file_json(payload)
    emit_json_output(payload, output)
    console.print("Link tracing complete")
    logger.info("Link tracing complete")
    return 0


@main.command("index")
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
@click.option(
    "-e",
    "--exclude-dir",
    "extra_exclude_dir",
    multiple=True,
    metavar="DIR",
    help="Additional directory name to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude-dir entries",
)
def index_cmd(
    vault_root: Path | None,
    output: Path | None,
    debug: bool,
    verbose: bool,
    extra_exclude_dir: tuple[str, ...],
    no_default_excludes: bool,
) -> int:
    """Output the scanned vault index as JSON."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug("Starting vault index scan", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("Scanning vault index", vault_root=str(vault_root))
    vault_index = scan_vault(
        vault_root, extra_exclude_dir=extra_exclude_dir, no_default_excludes=no_default_excludes
    )
    payload = json.dumps(asdict(vault_index), indent=2, default=str)
    payload = collapse_vault_file_json(payload)
    emit_json_output(payload, output)
    console.print("Vault index scan complete")
    logger.info("Vault index scan complete")
    return 0


@main.command("edges")
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
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["edge_list", "adjacency_list"], case_sensitive=False),
    default="edge_list",
    help="Output graph representation",
)
@click.option(
    "-e",
    "--exclude-dir",
    "extra_exclude_dir",
    multiple=True,
    metavar="DIR",
    help="Additional directory name to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude-dir entries",
)
def edge_list(
    vault_root: Path | None,
    output: Path | None,
    debug: bool,
    verbose: bool,
    fmt: str,
    extra_exclude_dir: tuple[str, ...],
    no_default_excludes: bool,
) -> int:
    """Output a resolved edge list with lightweight `VaultFile` entries."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug("Starting vault edge list", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("Building vault edge list", vault_root=str(vault_root))
    vault_index = scan_vault(
        vault_root, extra_exclude_dir=extra_exclude_dir, no_default_excludes=no_default_excludes
    )
    vault_registry = VaultRegistry(vault_index)

    if fmt == "adjacency_list":
        vault_graph = build_vault_digraph(vault_index)
        payload = json.dumps(_serialize_adjacency_list(vault_graph, vault_registry), indent=2)
    else:
        vault_graph = build_vault_digraph(vault_index)
        payload = json.dumps(_serialize_edge_list(vault_graph, vault_registry), indent=2)

    payload = collapse_vault_file_json(payload)
    emit_json_output(payload, output)
    console.print("Vault edge list complete")
    logger.info("Vault edge list complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
