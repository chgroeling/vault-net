"""Graph transform utilities for serialized output payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from vault_net.models import LayerEntry, VaultGraph, VaultLayered

if TYPE_CHECKING:
    from vault_net.models import VaultFile
    from vault_net.vault_registry import VaultRegistry


def build_vault_edge_list(
    graph: VaultGraph,
    vault_registry: VaultRegistry,
) -> list[list[VaultFile]]:
    """Return a resolved edge list with source/target `VaultFile` pairs."""
    edges: list[list[VaultFile]] = []
    for source_slug, target_slug in sorted(graph.digraph.edges()):
        source_file = vault_registry.get_file(source_slug)
        target_file = vault_registry.get_file(target_slug)
        if source_file is None or target_file is None:
            continue
        edges.append([source_file.to_file(), target_file.to_file()])

    return edges


def build_adjacency_list(
    graph: VaultGraph,
    vault_registry: VaultRegistry,
) -> dict[str, list[VaultFile]]:
    """Return source slug to resolved target `VaultFile` list."""
    payload: dict[str, list[VaultFile]] = {}
    for source_slug in sorted(graph.digraph.nodes()):
        source_note = vault_registry.get_file(str(source_slug))
        if source_note is None:
            continue

        targets: list[VaultFile] = []
        for target_slug in sorted(graph.digraph.successors(source_slug)):
            target_note = vault_registry.get_file(str(target_slug))
            if target_note is None:
                continue
            targets.append(target_note.to_file())
        payload[source_note.slug] = targets

    return payload


def build_layered_repr(source_slug: str, graph: VaultGraph) -> VaultLayered:
    """Transform an ego graph into a flat BFS depth-layer list."""
    layers: list[LayerEntry] = []
    for depth, nodes in enumerate(nx.bfs_layers(graph.digraph.to_undirected(), [source_slug])):
        layers.extend(LayerEntry(depth=depth, note=str(node)) for node in nodes)

    return VaultLayered(
        source_note=source_slug,
        vault_root=str(graph.vault_root),
        total_files=graph.digraph.number_of_nodes(),
        layers=layers,
    )


__all__ = ["build_adjacency_list", "build_layered_repr", "build_vault_edge_list"]
