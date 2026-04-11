"""Graph view utilities for serialized output payloads."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, cast

from rich.console import Group
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from vault_net.domain.models import NoteShow, VaultFile, VaultGraph, VaultIndex
    from vault_net.domain.services.vault_registry import VaultRegistry


class _LayerEntry(TypedDict):
    depth: int
    note: VaultFile


class _LayeredRepr(TypedDict):
    source_note: str
    vault_root: str
    total_files: int
    layers: list[_LayerEntry]


class _Registry(Protocol):
    def get_file(self, slug: str) -> Any | None: ...


class _RegistryNote(Protocol):
    slug: str

    def to_file(self) -> VaultFile: ...


def _slug_text(value: str) -> Text:
    return Text(value, style="yellow")


def _path_text(value: str) -> Text:
    return Text(value, style="cyan")


def _depth_text(depth: int) -> Text:
    return Text(str(depth), style="green")


def _hash_text(value: str) -> Text:
    return Text(value, style="magenta")


def _strip_path_and_ext(path: str) -> str:
    return Path(path).stem


def build_vault_edge_list(
    graph: VaultGraph,
    vault_registry: _Registry,
) -> list[list[VaultFile]]:
    """Return a resolved edge list with source/target `VaultFile` pairs."""
    edges: list[list[VaultFile]] = []
    for source_slug, target_slug in sorted(graph.digraph.edges()):
        source_file = vault_registry.get_file(source_slug)
        target_file = vault_registry.get_file(target_slug)
        if source_file is None or target_file is None:
            continue
        source_note = cast("_RegistryNote", source_file)
        target_note = cast("_RegistryNote", target_file)
        edges.append([source_note.to_file(), target_note.to_file()])

    return edges


def build_adjacency_list(
    graph: VaultGraph,
    vault_registry: _Registry,
) -> dict[str, list[VaultFile]]:
    """Return source slug to resolved target `VaultFile` list."""
    payload: dict[str, list[VaultFile]] = {}
    for source_slug in sorted(graph.digraph.nodes()):
        source_note = vault_registry.get_file(str(source_slug))
        if source_note is None:
            continue
        resolved_source = cast("_RegistryNote", source_note)

        targets: list[VaultFile] = []
        for target_slug in sorted(graph.digraph.successors(source_slug)):
            target_note = vault_registry.get_file(str(target_slug))
            if target_note is None:
                continue
            resolved_target = cast("_RegistryNote", target_note)
            targets.append(resolved_target.to_file())
        payload[resolved_source.slug] = targets

    return payload


def build_layered_repr(
    source_slug: str,
    graph: VaultGraph,
    vault_registry: _Registry,
) -> _LayeredRepr:
    """Transform an ego graph into a flat BFS depth-layer dictionary."""
    layers: list[_LayerEntry] = []
    for depth, nodes in enumerate(graph.digraph.bfs_layers(source_slug)):
        for node in nodes:
            note = vault_registry.get_file(str(node))
            if note is None:
                continue
            resolved_note = cast("_RegistryNote", note)
            layers.append({"depth": depth, "note": resolved_note.to_file()})

    return {
        "source_note": source_slug,
        "vault_root": str(graph.vault_root),
        "total_files": graph.digraph.number_of_nodes(),
        "layers": layers,
    }


def build_note_show(note_show: NoteShow) -> dict[str, object]:
    """Serialize a NoteShow result into a JSON-friendly dictionary."""
    from dataclasses import asdict

    return {
        "note": asdict(note_show.note),
        "forward_links": [asdict(f) for f in note_show.forward_links],
        "backward_links": [asdict(b) for b in note_show.backward_links],
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
        layers.append(
            {
                "depth": entry.get("depth", 0),
                "note": dict(note)
                if hasattr(note, "__iter__") and not isinstance(note, str)
                else note,
            }
        )

    return {
        "source_note": layered.get("source_note", source_slug),
        "vault_root": layered.get("vault_root", str(graph.vault_root)),
        "total_files": layered.get("total_files", graph.digraph.number_of_nodes()),
        "layers": layers,
    }


def _serialize_edge_list(graph: VaultGraph, vault_registry: VaultRegistry) -> dict[str, object]:
    from dataclasses import asdict

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
    from dataclasses import asdict

    adjacency = build_adjacency_list(graph, vault_registry)
    return {
        source_slug: [asdict(target_file) for target_file in target_files]
        for source_slug, target_files in adjacency.items()
    }


def _render_edge_list_table(
    graph: VaultGraph, vault_registry: VaultRegistry, use_basename: bool = False
) -> Table:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Src Slug", no_wrap=True, min_width=8)
    table.add_column("Tgt Slug", no_wrap=True, min_width=8)
    table.add_column("Source Name" if use_basename else "Source Path", no_wrap=True, max_width=50)
    table.add_column("Target Name" if use_basename else "Target Path", no_wrap=True, max_width=50)

    for source, target in build_vault_edge_list(graph, vault_registry):
        table.add_row(
            _slug_text(source.slug),
            _slug_text(target.slug),
            _path_text(_strip_path_and_ext(source.file_path) if use_basename else source.file_path),
            _path_text(_strip_path_and_ext(target.file_path) if use_basename else target.file_path),
        )

    return table


def _render_adjacency_list_table(
    graph: VaultGraph, vault_registry: VaultRegistry, use_basename: bool = False
) -> Table:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slug", no_wrap=True, min_width=8)
    table.add_column("Name" if use_basename else "Path", no_wrap=True, max_width=50)
    table.add_column("Targets", no_wrap=True, max_width=30)

    for source_slug in sorted(graph.digraph.nodes()):
        source_note = vault_registry.get_file(str(source_slug))
        if source_note is None:
            continue

        target_slugs: list[str] = []
        for target_slug in sorted(graph.digraph.successors(source_slug)):
            if vault_registry.get_file(str(target_slug)) is None:
                continue
            target_slugs.append(str(target_slug))

        file_path = source_note.file_path
        table.add_row(
            _slug_text(source_note.slug),
            _path_text(_strip_path_and_ext(file_path) if use_basename else file_path),
            _slug_text(", ".join(target_slugs) if target_slugs else "-"),
        )

    return table


def _render_layered_table(
    source_slug: str, graph: VaultGraph, vault_registry: VaultRegistry, use_basename: bool = False
) -> Table:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slug", no_wrap=True, min_width=8)
    table.add_column("Depth", no_wrap=True, max_width=6)
    table.add_column("Name" if use_basename else "Path", no_wrap=True, max_width=50)

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
        table.add_row(
            _slug_text(slug),
            _depth_text(depth),
            _path_text(_strip_path_and_ext(path) if use_basename else path),
        )

    return table


def _render_note_show_table(note_show: NoteShow, use_basename: bool = False) -> Group:
    info_table = Table(show_header=False, box=None, pad_edge=False)
    info_table.add_column("Key", no_wrap=True, max_width=15)
    info_table.add_column("Value", no_wrap=False)

    info_table.add_row("Slug", _slug_text(note_show.note.slug))
    info_table.add_row("Path", _path_text(note_show.note.file_path))
    info_table.add_row("Hash", _hash_text(note_show.note.file_hash))
    info_table.add_row("Status", note_show.note.status)
    if note_show.note.error:
        info_table.add_row("Error", note_show.note.error)
    if note_show.note.frontmatter:
        info_table.add_row("Frontmatter", str(note_show.note.frontmatter))
    info_table.add_row(
        "Size",
        str(note_show.note.stats.file_size) if note_show.note.stats.file_size else "N/A",
    )
    info_table.add_row(
        "Modified",
        note_show.note.stats.modified_time or "N/A",
    )
    info_table.add_row(
        "Accessed",
        note_show.note.stats.access_time or "N/A",
    )

    forward_table = Table(show_header=True, header_style="bold", box=None)
    forward_table.add_column("Slug", no_wrap=True, max_width=8)
    forward_table.add_column("Name" if use_basename else "Path", no_wrap=False)
    for link in sorted(note_show.forward_links, key=lambda f: f.slug):
        forward_table.add_row(
            _slug_text(link.slug),
            _path_text(_strip_path_and_ext(link.file_path) if use_basename else link.file_path),
        )

    backward_table = Table(show_header=True, header_style="bold", box=None)
    backward_table.add_column("Slug", no_wrap=True, max_width=8)
    backward_table.add_column("Name" if use_basename else "Path", no_wrap=False)
    for link in sorted(note_show.backward_links, key=lambda f: f.slug):
        backward_table.add_row(
            _slug_text(link.slug),
            _path_text(_strip_path_and_ext(link.file_path) if use_basename else link.file_path),
        )

    info_header = Text("Note Information", style="bold cyan")

    forward_header = Text(f"Forward Links ({len(note_show.forward_links)})", style="bold cyan")
    backward_header = Text(f"Backward Links ({len(note_show.backward_links)})", style="bold cyan")

    return Group(
        info_header,
        Padding(info_table, (0, 0, 0, 1)),
        "",
        forward_header,
        forward_table if note_show.forward_links else Text(" None", style="dim"),
        "",
        backward_header,
        backward_table if note_show.backward_links else Text(" None", style="dim"),
    )


def _render_index_table(vault_index: VaultIndex, use_basename: bool = False) -> Group:
    """Render vault index as a table with file stats."""
    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
    )
    table.add_column("Slug", no_wrap=True, min_width=8)
    table.add_column("Size", no_wrap=True, justify="right", max_width=10)
    table.add_column("Modified", no_wrap=True, max_width=26)
    table.add_column("Accessed", no_wrap=True, max_width=26)
    table.add_column("Name" if use_basename else "Path", no_wrap=False, ratio=1)

    for note in sorted(vault_index.files, key=lambda n: n.slug):
        file_size = str(note.stats.file_size) if note.stats.file_size else "N/A"
        modified = note.stats.modified_time or "N/A"
        accessed = note.stats.access_time or "N/A"
        table.add_row(
            _slug_text(note.slug),
            file_size,
            modified,
            accessed,
            _path_text(_strip_path_and_ext(note.file_path) if use_basename else note.file_path),
        )

    header = Text(f"Vault Index ({vault_index.metadata.total_files} files)", style="bold cyan")
    return Group(header, "", table)
