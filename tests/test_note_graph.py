"""Unit tests for ego graph extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from vault_net import build_note_ego_graph, build_vault_digraph, scan_vault


def test_build_note_ego_graph_rejects_negative_depth(tmp_path: Path) -> None:
    """Negative depth raises ValueError."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("", encoding="utf-8")

    graph = build_vault_digraph(scan_vault(vault_root)).digraph
    with pytest.raises(ValueError, match="depth must be >= 0"):
        build_note_ego_graph("a.md", graph, depth=-1)


def test_build_note_ego_graph_requires_known_slug(tmp_path: Path) -> None:
    """Unknown slug raises KeyError."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("", encoding="utf-8")

    graph = build_vault_digraph(scan_vault(vault_root)).digraph
    with pytest.raises(KeyError):
        build_note_ego_graph("missing.md", graph, depth=1)


def test_build_note_ego_graph_depth_zero_returns_source_only(tmp_path: Path) -> None:
    """Depth zero keeps only the source node and no edges."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("", encoding="utf-8")

    graph = build_vault_digraph(scan_vault(vault_root)).digraph
    ego = build_note_ego_graph("a.md", graph, depth=0)

    assert sorted(ego.nodes()) == ["a.md"]
    assert list(ego.edges()) == []


def test_build_note_ego_graph_uses_undirected_neighborhood(tmp_path: Path) -> None:
    """Depth one includes outgoing links and backlinks."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("", encoding="utf-8")
    (vault_root / "c.md").write_text("[[a]]", encoding="utf-8")

    graph = build_vault_digraph(scan_vault(vault_root)).digraph
    ego = build_note_ego_graph("a.md", graph, depth=1)

    assert sorted(ego.nodes()) == ["a.md", "b.md", "c.md"]
    assert sorted(ego.edges()) == [("a.md", "b.md"), ("c.md", "a.md")]
