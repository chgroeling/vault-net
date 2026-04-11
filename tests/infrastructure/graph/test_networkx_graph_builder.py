"""Infrastructure graph adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from vault_net.domain.models import VaultGraph, VaultIndex
from vault_net.infrastructure.graph.networkx_graph_builder import NetworkXGraphBuilder
from vault_net.infrastructure.scanner.matterify_scanner import MatterifyVaultScanner


def _create_vault(tmp_path: Path, notes: dict[str, str]) -> Path:
    """Create a temporary vault from relative file paths to markdown content."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    for file_path, content in notes.items():
        note_path = vault_root / file_path
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(content, encoding="utf-8")

    return vault_root


def _slug_for(vault_index: VaultIndex, file_path: str) -> str:
    """Return slug for a scanned file path."""
    return next(file.slug for file in vault_index.files if file.file_path == file_path)


def test_build_full_graph_resolves_known_links_only(tmp_path: Path) -> None:
    """Resolved links are included and unresolved targets are omitted."""
    vault_root = _create_vault(
        tmp_path,
        {
            "home.md": "[[about]]\n[[missing]]\n",
            "about.md": "",
        },
    )

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    vault_index = scanner.scan(vault_root)
    vault_graph = graph_builder.build_full_graph(vault_index)
    home_slug = _slug_for(vault_index, "home.md")
    about_slug = _slug_for(vault_index, "about.md")

    assert isinstance(vault_graph, VaultGraph)
    assert sorted(vault_graph.digraph.edges()) == [(home_slug, about_slug)]
    assert vault_graph.metadata.edge_count == 1


def test_build_full_graph_includes_isolated_notes(tmp_path: Path) -> None:
    """Digraph includes all scanned notes, including isolated ones."""
    vault_root = _create_vault(
        tmp_path,
        {
            "home.md": "[[about]]\n",
            "about.md": "",
            "isolated.md": "",
        },
    )

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    vault_index = scanner.scan(vault_root)
    vault_graph = graph_builder.build_full_graph(vault_index)
    home_slug = _slug_for(vault_index, "home.md")
    about_slug = _slug_for(vault_index, "about.md")

    assert sorted(vault_graph.digraph.nodes()) == sorted(file.slug for file in vault_index.files)
    assert sorted(vault_graph.digraph.edges()) == [(home_slug, about_slug)]


def test_build_full_graph_skips_self_loops_and_deduplicates_edges(tmp_path: Path) -> None:
    """Self-links are filtered and repeated links collapse into one edge."""
    vault_root = _create_vault(
        tmp_path,
        {
            "home.md": "[[home]]\n[[about]]\n[[about]]\n",
            "about.md": "",
        },
    )

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    vault_index = scanner.scan(vault_root)
    vault_graph = graph_builder.build_full_graph(vault_index)
    home_slug = _slug_for(vault_index, "home.md")
    about_slug = _slug_for(vault_index, "about.md")

    assert sorted(vault_graph.digraph.edges()) == [(home_slug, about_slug)]
    assert vault_graph.metadata.edge_count == 1


def test_build_neighborhood_graph_rejects_negative_depth(tmp_path: Path) -> None:
    """Negative depth raises ValueError."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    vault_index = scanner.scan(vault_root)
    graph = graph_builder.build_full_graph(vault_index)
    a_slug = _slug_for(vault_index, "a.md")
    with pytest.raises(ValueError, match="depth must be >= 0"):
        graph_builder.build_neighborhood_graph(a_slug, graph, depth=-1)


def test_build_neighborhood_graph_requires_known_slug(tmp_path: Path) -> None:
    """Unknown slug raises KeyError."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    graph = graph_builder.build_full_graph(scanner.scan(vault_root))
    with pytest.raises(KeyError):
        graph_builder.build_neighborhood_graph("missing----", graph, depth=1)


def test_build_neighborhood_graph_depth_zero_returns_source_only(tmp_path: Path) -> None:
    """Depth zero keeps only the source node and no edges."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    vault_index = scanner.scan(vault_root)
    graph = graph_builder.build_full_graph(vault_index)
    a_slug = _slug_for(vault_index, "a.md")
    ego = graph_builder.build_neighborhood_graph(a_slug, graph, depth=0).digraph

    assert sorted(ego.nodes()) == [a_slug]
    assert list(ego.edges()) == []


def test_build_neighborhood_graph_uses_undirected_neighborhood(tmp_path: Path) -> None:
    """Depth one includes outgoing links and backlinks."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("", encoding="utf-8")
    (vault_root / "c.md").write_text("[[a]]", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    graph_builder = NetworkXGraphBuilder()
    vault_index = scanner.scan(vault_root)
    graph = graph_builder.build_full_graph(vault_index)
    a_slug = _slug_for(vault_index, "a.md")
    b_slug = _slug_for(vault_index, "b.md")
    c_slug = _slug_for(vault_index, "c.md")
    ego = graph_builder.build_neighborhood_graph(a_slug, graph, depth=1).digraph

    assert sorted(ego.nodes()) == [a_slug, b_slug, c_slug]
    assert sorted(ego.edges()) == [(a_slug, b_slug), (c_slug, a_slug)]
