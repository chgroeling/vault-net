"""CLI entry point for vault-net."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import TextIO

import click
import structlog
from rich.console import Console

from vault_net import __version__
from vault_net.application import (
    create_note,
    get_full_graph,
    scan_vault,
    show_note,
    trace_note_links,
)
from vault_net.domain.services.vault_registry import VaultRegistry
from vault_net.interface.formatters.views import (
    _render_adjacency_list_table,
    _render_edge_list_table,
    _render_index_table,
    _render_layered_table,
    _render_note_show_table,
    _serialize_adjacency_list,
    _serialize_edge_list,
    _serialize_layered_repr,
    build_note_show,
)
from vault_net.logging import configure_debug_logging, get_console

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


def emit_pretty_output(renderable: object, output: Path | None) -> None:
    """Emit rich renderable to stdout or a target file."""
    if output is None:
        Console().print(renderable)
        return

    try:
        output_buffer = StringIO()
        output_console = Console(file=output_buffer, force_terminal=False, color_system=None)
        output_console.print(renderable)
        rendered = output_buffer.getvalue()
        output.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Could not write output file {output}: {exc}") from exc


@click.group()
def main() -> None:
    """Trace Obsidian note links to filesystem sources."""


@main.command("trace")
@click.version_option(version=__version__)
@click.argument("note_input", type=str)
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
    "--exclude",
    "extra_exclude",
    multiple=True,
    metavar="GLOB",
    help="Additional glob pattern to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude entries",
)
@click.option(
    "--basename",
    is_flag=True,
    help="Show only filenames without path or extension in pretty output",
)
def trace_cmd(
    note_input: str,
    vault_root: Path | None,
    depth: int,
    output: Path | None,
    debug: bool,
    verbose: bool,
    style: str,
    output_format: str,
    extra_exclude: tuple[str, ...],
    no_default_excludes: bool,
    basename: bool,
) -> int:
    """Trace links for a single note (specify by slug or file path)."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "starting.link_tracer",
        note_input=note_input,
        vault_root=str(vault_root) if vault_root else None,
    )
    vault_root = resolve_vault_root(vault_root)
    logger.info("tracing.links", note_input=note_input)

    try:
        trace_result = trace_note_links(
            vault_root,
            note_input,
            depth=depth,
            extra_exclude=extra_exclude,
            no_default_excludes=no_default_excludes,
        )
    except KeyError as exc:
        raise click.UsageError(f"Unknown slug '{note_input}'.") from exc

    vault_registry = VaultRegistry(trace_result.vault_index)
    neighborhood_graph = trace_result.neighborhood_graph
    slug = trace_result.source_slug

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
        emit_pretty_output(
            _render_layered_table(slug, neighborhood_graph, vault_registry, basename),
            output,
        )
    elif style == "adjacency_list":
        emit_pretty_output(
            _render_adjacency_list_table(neighborhood_graph, vault_registry, basename), output
        )
    else:
        emit_pretty_output(
            _render_edge_list_table(neighborhood_graph, vault_registry, basename), output
        )
    console.print("Link tracing complete")
    logger.info("link.tracing.complete")
    return 0


@main.command("index")
@click.version_option(version=__version__)
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
    "--exclude",
    "extra_exclude",
    multiple=True,
    metavar="GLOB",
    help="Additional glob pattern to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude entries",
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
    "--basename",
    is_flag=True,
    help="Show only filenames without path or extension in pretty output",
)
def index_cmd(
    vault_root: Path | None,
    output: Path | None,
    debug: bool,
    verbose: bool,
    extra_exclude: tuple[str, ...],
    no_default_excludes: bool,
    output_format: str,
    basename: bool,
) -> int:
    """Output the scanned vault index as JSON or pretty table."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug("starting.vault_index_scan", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("scanning.vault.index", vault_root=str(vault_root))
    vault_index, _ = scan_vault(
        vault_root,
        extra_exclude=extra_exclude,
        no_default_excludes=no_default_excludes,
    )

    if output_format == "json":
        payload = json.dumps(asdict(vault_index), indent=2, default=str)
        emit_json_output(payload, output)
    else:
        emit_pretty_output(_render_index_table(vault_index, basename), output)

    console.print("Vault index scan complete")
    logger.info("vault.index.scan.complete")
    return 0


@main.command("graph")
@click.version_option(version=__version__)
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
    "--exclude",
    "extra_exclude",
    multiple=True,
    metavar="GLOB",
    help="Additional glob pattern to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude entries",
)
@click.option(
    "--basename",
    is_flag=True,
    help="Show only filenames without path or extension in pretty output",
)
def graph_cmd(
    vault_root: Path | None,
    output: Path | None,
    debug: bool,
    verbose: bool,
    style: str,
    output_format: str,
    extra_exclude: tuple[str, ...],
    no_default_excludes: bool,
    basename: bool,
) -> int:
    """Output a resolved edge list with lightweight `VaultFile` entries."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug("starting.vault_edge_list", vault_root=str(vault_root) if vault_root else None)
    vault_root = resolve_vault_root(vault_root)
    logger.info("building.vault.edge_list", vault_root=str(vault_root))
    vault_index, note_links = scan_vault(
        vault_root,
        extra_exclude=extra_exclude,
        no_default_excludes=no_default_excludes,
    )
    vault_registry = VaultRegistry(vault_index)
    vault_graph = get_full_graph(vault_index, note_links)

    payload_obj: object
    if style == "adjacency_list":
        payload_obj = _serialize_adjacency_list(vault_graph, vault_registry)
    else:
        payload_obj = _serialize_edge_list(vault_graph, vault_registry)

    if output_format == "json":
        emit_json_output(json.dumps(payload_obj, indent=2), output)
    elif style == "adjacency_list":
        emit_pretty_output(
            _render_adjacency_list_table(vault_graph, vault_registry, basename), output
        )
    else:
        emit_pretty_output(_render_edge_list_table(vault_graph, vault_registry, basename), output)
    console.print("Vault edge list complete")
    logger.info("vault.edge.list.complete")
    return 0


@main.command("show")
@click.version_option(version=__version__)
@click.argument("note_input", type=str)
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
    "--format",
    "output_format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    show_default=True,
    help="Output format",
)
@click.option(
    "-e",
    "--exclude",
    "extra_exclude",
    multiple=True,
    metavar="GLOB",
    help="Additional glob pattern to exclude from traversal (repeatable)",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    help="Disable built-in default exclusions; use only --exclude entries",
)
@click.option(
    "--basename",
    is_flag=True,
    help="Show only filenames without path or extension in pretty output",
)
@click.option(
    "--no-content",
    is_flag=True,
    help="Suppress loading and displaying file content",
)
def show_cmd(
    note_input: str,
    vault_root: Path | None,
    output: Path | None,
    debug: bool,
    verbose: bool,
    output_format: str,
    extra_exclude: tuple[str, ...],
    no_default_excludes: bool,
    basename: bool,
    no_content: bool,
) -> int:
    """Show detailed information about a note including forward and backward links."""
    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "starting.show_note",
        note_input=note_input,
        vault_root=str(vault_root) if vault_root else None,
    )
    vault_root = resolve_vault_root(vault_root)
    logger.info("showing.note", note_input=note_input)

    try:
        note_show = show_note(
            vault_root,
            note_input,
            extra_exclude=extra_exclude,
            no_default_excludes=no_default_excludes,
            include_content=not no_content,
        )
    except KeyError as exc:
        raise click.UsageError(f"Unknown slug '{note_input}'.") from exc

    if output_format == "json":
        payload = build_note_show(note_show)
        emit_json_output(json.dumps(payload, indent=2, default=str), output)
    else:
        emit_pretty_output(_render_note_show_table(note_show, basename), output)

    console.print("Note show complete")
    logger.info("note.show.complete")
    return 0


@main.command("create")
@click.version_option(version=__version__)
@click.argument("name", type=str)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Vault root directory (overrides VAULT_ROOT env and .vault file)",
)
@click.option(
    "-c",
    "--content",
    type=str,
    default=None,
    help="Text content to write into the new note",
)
@click.option(
    "-f",
    "--content-file",
    type=click.File("r", encoding="utf-8"),
    default=None,
    help="Read note content from a file (use '-' for stdin)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite the note if it already exists",
)
@click.option("--debug", is_flag=True, help="Enable debug-level structured logging to stderr")
@click.option("--verbose", is_flag=True, help="Enable verbose console output")
def create_cmd(
    name: str,
    vault_root: Path | None,
    content: str | None,
    content_file: TextIO | None,
    force: bool,
    debug: bool,
    verbose: bool,
) -> int:
    """Create a new note in the vault.

    NAME is the note path relative to the vault root (e.g. "sub/dir/my-note").
    A .md extension is appended automatically when missing.
    """
    if content is not None and content_file is not None:
        raise click.UsageError("--content and --content-file are mutually exclusive.")

    if content_file is not None:
        content = content_file.read()
    elif content is None:
        content = ""

    configure_debug_logging(debug)
    console = get_console(verbose)

    logger.debug(
        "starting.create_note",
        name=name,
        vault_root=str(vault_root) if vault_root else None,
    )
    vault_root = resolve_vault_root(vault_root)
    logger.info("creating.note", name=name)

    try:
        slug = create_note(vault_root, name, content=content, force=force)
    except FileExistsError as exc:
        raise click.UsageError(str(exc)) from exc
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    click.echo(slug)
    console.print("Note created")
    logger.info("note.created", slug=slug)
    return 0
