"""CLI entry point for vault-net."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import click
import structlog
from rich.console import Console
from rich.table import Table
from rich.text import Text

from vault_net.application import (
    get_full_graph,
    scan_vault,
    trace_note_links,
)
from vault_net.domain.services.vault_registry import VaultRegistry
from vault_net.interface.formatters.views import (
    build_adjacency_list,
    build_layered_repr,
    build_vault_edge_list,
)
from vault_net.logging import configure_debug_logging, get_console

if TYPE_CHECKING:
    from vault_net.domain.models import VaultGraph

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
    """Emit JSON payload to stdout or a target file."""
    if output is None:
        click.echo(payload)
        return

    try:
        output.write_text(f"{payload}\n", encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Could not write output file {output}: {exc}") from exc


def emit_pretty_output(table: Table, output: Path | None) -> None:
    """Emit rich table to stdout or a target file."""
    if output is None:
        Console().print(table)
        return

    try:
        output_buffer = StringIO()
        output_console = Console(file=output_buffer, force_terminal=False, color_system=None)
        output_console.print(table)
        rendered = output_buffer.getvalue()
        output.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Could not write output file {output}: {exc}") from exc


def _slug_text(value: str) -> Text:
    return Text(value, style="yellow")


def _path_text(value: str) -> Text:
    return Text(value, style="cyan")


def _depth_text(depth: int) -> Text:
    return Text(str(depth), style="green")


def _render_edge_list_table(graph: VaultGraph, vault_registry: VaultRegistry) -> Table:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Src Slug")
    table.add_column("Tgt Slug")
    table.add_column("Source Path")
    table.add_column("Target Path")

    for source, target in build_vault_edge_list(graph, vault_registry):
        table.add_row(
            _slug_text(source.slug),
            _slug_text(target.slug),
            _path_text(source.file_path),
            _path_text(target.file_path),
        )

    return table


def _render_adjacency_list_table(graph: VaultGraph, vault_registry: VaultRegistry) -> Table:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slug")
    table.add_column("Path")
    table.add_column("Targets")

    for source_slug in sorted(graph.digraph.nodes()):
        source_note = vault_registry.get_file(str(source_slug))
        if source_note is None:
            continue

        target_slugs: list[str] = []
        for target_slug in sorted(graph.digraph.successors(source_slug)):
            if vault_registry.get_file(str(target_slug)) is None:
                continue
            target_slugs.append(str(target_slug))

        table.add_row(
            _slug_text(source_note.slug),
            _path_text(source_note.file_path),
            _slug_text(", ".join(target_slugs) if target_slugs else "-"),
        )

    return table


def _render_layered_table(
    source_slug: str, graph: VaultGraph, vault_registry: VaultRegistry
) -> Table:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slug")
    table.add_column("Depth")
    table.add_column("Path")

    layered = _serialize_layered_repr(source_slug, graph, vault_registry)
    raw_layers = layered.get("layers", [])
    if not isinstance(raw_layers, list):
        return table

    for entry in raw_layers:
        if not isinstance(entry, dict):
            continue
        note = entry.get("note")
        if not isinstance(note, dict):
            continue
        slug = note.get("slug")
        path = note.get("file_path")
        depth = entry.get("depth")
        if not isinstance(slug, str) or not isinstance(path, str) or not isinstance(depth, int):
            continue
        table.add_row(_slug_text(slug), _depth_text(depth), _path_text(path))

    return table


@click.group()
def main() -> None:
    """Trace Obsidian note links to filesystem sources."""


def _serialize_edge_list(graph: VaultGraph, vault_registry: VaultRegistry) -> dict[str, object]:
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
    adjacency = build_adjacency_list(graph, vault_registry)
    return {
        source_slug: [asdict(target_file) for target_file in target_files]
        for source_slug, target_files in adjacency.items()
    }


def _serialize_layered_repr(
    source_slug: str,
    graph: VaultGraph,
    vault_registry: VaultRegistry,
) -> dict[str, object]:
    layered = build_layered_repr(source_slug, graph, vault_registry)
    raw_layers = layered.get("layers", [])
    if not isinstance(raw_layers, list):
        return layered

    layers: list[dict[str, object]] = []
    for entry in raw_layers:
        if not isinstance(entry, dict):
            continue
        note = entry.get("note")
        if note is None:
            continue
        layers.append({"depth": entry.get("depth", 0), "note": asdict(note)})

    return {
        "source_note": layered.get("source_note", source_slug),
        "vault_root": layered.get("vault_root", str(graph.vault_root)),
        "total_files": layered.get("total_files", graph.digraph.number_of_nodes()),
        "layers": layers,
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
    help="Write output to file instead of stdout",
)
@click.option("--debug", is_flag=True, help="Enable debug-level structured logging to stderr")
@click.option("--verbose", is_flag=True, help="Enable verbose console output")
@click.option(
    "--style",
    "style",
    type=click.Choice(["edge_list", "adjacency_list", "layered"], case_sensitive=False),
    default="edge_list",
    help="Graph representation style",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    show_default=True,
    help="Output format",
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
    style: str,
    output_format: str,
    extra_exclude_dir: tuple[str, ...],
    no_default_excludes: bool,
) -> int:
    """Trace links for a single note."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "starting.link_tracer", slug=slug, vault_root=str(vault_root) if vault_root else None
    )
    vault_root = resolve_vault_root(vault_root)
    logger.info("tracing.links", slug=slug)

    try:
        trace_result = trace_note_links(
            vault_root,
            slug,
            depth=depth,
            extra_exclude_dir=extra_exclude_dir,
            no_default_excludes=no_default_excludes,
        )
    except KeyError as exc:
        raise click.UsageError(f"Unknown slug '{slug}'.") from exc

    vault_registry = VaultRegistry(trace_result.vault_index)
    neighborhood_graph = trace_result.neighborhood_graph

    payload_obj: object
    if style == "layered":
        payload_obj = _serialize_layered_repr(slug, neighborhood_graph, vault_registry)
    elif style == "adjacency_list":
        payload_obj = _serialize_adjacency_list(neighborhood_graph, vault_registry)
    else:
        payload_obj = _serialize_edge_list(neighborhood_graph, vault_registry)

    if output_format == "json":
        emit_json_output(json.dumps(payload_obj, indent=2), output)
    elif style == "layered":
        emit_pretty_output(_render_layered_table(slug, neighborhood_graph, vault_registry), output)
    elif style == "adjacency_list":
        emit_pretty_output(_render_adjacency_list_table(neighborhood_graph, vault_registry), output)
    else:
        emit_pretty_output(_render_edge_list_table(neighborhood_graph, vault_registry), output)
    console.print("Link tracing complete")
    logger.info("link.tracing.complete")
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
    help="Write output to file instead of stdout",
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

    logger.debug("starting.vault_index_scan", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("scanning.vault.index", vault_root=str(vault_root))
    vault_index = scan_vault(
        vault_root,
        extra_exclude_dir=extra_exclude_dir,
        no_default_excludes=no_default_excludes,
    )
    payload = json.dumps(asdict(vault_index), indent=2, default=str)
    emit_json_output(payload, output)
    console.print("Vault index scan complete")
    logger.info("vault.index.scan.complete")
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
    help="Write output to file instead of stdout",
)
@click.option("--debug", is_flag=True, help="Enable debug-level structured logging to stderr")
@click.option("--verbose", is_flag=True, help="Enable verbose console output")
@click.option(
    "--style",
    "style",
    type=click.Choice(["edge_list", "adjacency_list"], case_sensitive=False),
    default="edge_list",
    help="Graph representation style",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    show_default=True,
    help="Output format",
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
def graph_cmd(
    vault_root: Path | None,
    output: Path | None,
    debug: bool,
    verbose: bool,
    style: str,
    output_format: str,
    extra_exclude_dir: tuple[str, ...],
    no_default_excludes: bool,
) -> int:
    """Output a resolved edge list with lightweight `VaultFile` entries."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug("starting.vault_edge_list", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("building.vault.edge_list", vault_root=str(vault_root))
    vault_index = scan_vault(
        vault_root,
        extra_exclude_dir=extra_exclude_dir,
        no_default_excludes=no_default_excludes,
    )
    vault_registry = VaultRegistry(vault_index)
    vault_graph = get_full_graph(vault_index)

    payload_obj: object
    if style == "adjacency_list":
        payload_obj = _serialize_adjacency_list(vault_graph, vault_registry)
    else:
        payload_obj = _serialize_edge_list(vault_graph, vault_registry)

    if output_format == "json":
        emit_json_output(json.dumps(payload_obj, indent=2), output)
    elif style == "adjacency_list":
        emit_pretty_output(_render_adjacency_list_table(vault_graph, vault_registry), output)
    else:
        emit_pretty_output(_render_edge_list_table(vault_graph, vault_registry), output)
    console.print("Vault edge list complete")
    logger.info("vault.edge.list.complete")
    return 0
