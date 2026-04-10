"""Tests for graph transform functions."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from vault_net.models import LayerEntry, VaultGraph, VaultGraphMetadata, VaultLayered
from vault_net.transforms import build_layered_repr


def _build_graph(graph: nx.DiGraph[str]) -> VaultGraph:
    return VaultGraph(
        vault_root=Path("/vault"),
        metadata=VaultGraphMetadata(edge_count=graph.number_of_edges()),
        digraph=graph,
    )


def test_build_layered_repr_returns_vault_layered_type() -> None:
    """Return value is a VaultLayered instance."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node("home.md")
    result = build_layered_repr("home.md", _build_graph(graph))
    assert isinstance(result, VaultLayered)


def test_build_layered_repr_preserves_vault_root_and_total_files() -> None:
    """source note, root and size are forwarded correctly."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge("home.md", "about.md")

    result = build_layered_repr("home.md", _build_graph(graph))
    assert result.source_note == "home.md"
    assert result.vault_root == "/vault"
    assert result.total_files == 2


def test_build_layered_repr_empty_graph_yields_source_at_depth_zero() -> None:
    """Source note is always depth zero."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node("home.md")
    result = build_layered_repr("home.md", _build_graph(graph))
    assert result.layers == [LayerEntry(depth=0, note="home.md")]


def test_build_layered_repr_backlinks_appear_at_depth_one() -> None:
    """Reverse neighbors are included via undirected BFS."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge("other.md", "home.md")
    result = build_layered_repr("home.md", _build_graph(graph))
    depths = {entry.note: entry.depth for entry in result.layers}
    assert depths["home.md"] == 0
    assert depths["other.md"] == 1


def test_build_layered_repr_two_hop_note_appears_at_depth_two() -> None:
    """Two hops from source yields depth two."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge("home.md", "about.md")
    graph.add_edge("about.md", "projects.md")
    result = build_layered_repr("home.md", _build_graph(graph))
    depths = {entry.note: entry.depth for entry in result.layers}
    assert depths["home.md"] == 0
    assert depths["about.md"] == 1
    assert depths["projects.md"] == 2
