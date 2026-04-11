"""Interface formatter tests for graph view functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from vault_net.domain.models import VaultFile, VaultGraph, VaultGraphMetadata
from vault_net.domain.services.vault_registry import VaultRegistry
from vault_net.infrastructure.graph.networkx_vault_digraph import NetworkXVaultDiGraph
from vault_net.infrastructure.scanner.matterify_scanner import MatterifyVaultScanner
from vault_net.interface.formatters.views import build_layered_repr, build_vault_edge_list


@dataclass(frozen=True)
class _StubNote:
    slug: str

    def to_file(self) -> VaultFile:
        return VaultFile(slug=self.slug, file_path=self.slug)


class _StubRegistry:
    def __init__(self, slugs: set[str]) -> None:
        self._notes = {slug: _StubNote(slug=slug) for slug in slugs}

    def get_file(self, slug: str) -> _StubNote | None:
        return self._notes.get(slug)


def _build_graph(graph: nx.DiGraph[str]) -> VaultGraph:
    return VaultGraph(
        vault_root=Path("/vault"),
        metadata=VaultGraphMetadata(edge_count=graph.number_of_edges()),
        digraph=NetworkXVaultDiGraph(graph),
    )


def _build_registry(graph: nx.DiGraph[str]) -> _StubRegistry:
    return _StubRegistry(set(graph.nodes()))


def test_build_layered_repr_returns_dictionary() -> None:
    """Return value is a dictionary payload."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node("home.md")
    result = build_layered_repr("home.md", _build_graph(graph), _build_registry(graph))
    assert isinstance(result, dict)


def test_build_layered_repr_preserves_vault_root_and_total_files() -> None:
    """Source note, root and size are forwarded correctly."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge("home.md", "about.md")

    result = build_layered_repr("home.md", _build_graph(graph), _build_registry(graph))
    assert result["source_note"] == "home.md"
    assert result["vault_root"] == "/vault"
    assert result["total_files"] == 2


def test_build_layered_repr_empty_graph_yields_source_at_depth_zero() -> None:
    """Source note is always depth zero."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node("home.md")
    result = build_layered_repr("home.md", _build_graph(graph), _build_registry(graph))
    assert result["layers"] == [
        {"depth": 0, "note": VaultFile(slug="home.md", file_path="home.md")}
    ]


def test_build_layered_repr_backlinks_appear_at_depth_one() -> None:
    """Reverse neighbors are included via undirected BFS."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge("other.md", "home.md")
    result = build_layered_repr("home.md", _build_graph(graph), _build_registry(graph))
    layers = result["layers"]
    depths = {entry["note"].slug: entry["depth"] for entry in layers}
    assert depths["home.md"] == 0
    assert depths["other.md"] == 1


def test_build_layered_repr_two_hop_note_appears_at_depth_two() -> None:
    """Two hops from source yields depth two."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge("home.md", "about.md")
    graph.add_edge("about.md", "projects.md")
    result = build_layered_repr("home.md", _build_graph(graph), _build_registry(graph))
    layers = result["layers"]
    depths = {entry["note"].slug: entry["depth"] for entry in layers}
    assert depths["home.md"] == 0
    assert depths["about.md"] == 1
    assert depths["projects.md"] == 2


def test_build_vault_edge_list_returns_lightweight_vault_file_pairs(tmp_path: Path) -> None:
    """Edge list is represented as source/target `VaultFile` pairs."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("[[about]]\n", encoding="utf-8")
    (vault_root / "about.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    vault_index = scanner.scan(vault_root)
    vault_registry = VaultRegistry(vault_index)

    home_slug = next(f.slug for f in vault_index.files if f.file_path.endswith("home.md"))
    about_slug = next(f.slug for f in vault_index.files if f.file_path.endswith("about.md"))

    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_edge(home_slug, about_slug)
    vault_graph = _build_graph(graph)
    edges = build_vault_edge_list(vault_graph, vault_registry)

    assert len(edges) == 1
    assert edges[0][0].file_path.endswith("home.md")
    assert edges[0][1].file_path.endswith("about.md")
    assert not hasattr(edges[0][0], "links")
    assert not hasattr(edges[0][0], "frontmatter")
    assert not hasattr(edges[0][0], "stats")
