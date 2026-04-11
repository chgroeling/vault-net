"""Graph view utilities for serialized output payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypedDict, cast

if TYPE_CHECKING:
    from vault_net.domain.models import NoteShow, VaultFile, VaultGraph


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
