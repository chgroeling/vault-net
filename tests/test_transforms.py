"""Tests for graph transform functions."""

from __future__ import annotations

from link_tracer.models import (
    LayerEntry,
    LinkEdge,
    VaultGraph,
    VaultGraphMetadata,
    VaultLayered,
    VaultLink,
)
from link_tracer.transforms import to_layered


def _make_graph(edges: dict[str, list[LinkEdge]], total_files: int = 1) -> VaultGraph:
    """Build a minimal VaultGraph for testing."""
    return VaultGraph(
        vault_root="/vault",
        metadata=VaultGraphMetadata(
            source_directory="/vault",
            total_files=total_files,
            errors=0,
        ),
        edges=edges,
    )


def _wikilink(target: str) -> VaultLink:
    return VaultLink(link_type="WIKILINK", target=target, alias=None, heading=None, blockid=None)


def _edge(target_note: str) -> LinkEdge:
    return LinkEdge(link=_wikilink(target_note), resolved=True, target_note=target_note)


def _unresolved_edge(target: str) -> LinkEdge:
    return LinkEdge(
        link=_wikilink(target),
        resolved=False,
        target_note=None,
        unresolved_reason="not found",
    )


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_to_layered_returns_vault_layered_type() -> None:
    """Return value is a VaultLayered instance."""
    graph = _make_graph({})
    result = to_layered("home.md", graph)
    assert isinstance(result, VaultLayered)


def test_to_layered_preserves_vault_root_and_metadata() -> None:
    """vault_root, source_note and metadata are forwarded unchanged."""
    graph = _make_graph({})
    result = to_layered("home.md", graph)
    assert result.source_note == "home.md"
    assert result.vault_root == "/vault"
    assert result.metadata is graph.metadata


# ---------------------------------------------------------------------------
# Depth 0 — source note only
# ---------------------------------------------------------------------------


def test_to_layered_empty_graph_yields_source_at_depth_zero() -> None:
    """Source note is always placed at depth 0, even with no edges."""
    graph = _make_graph({})
    result = to_layered("home.md", graph)
    assert result.layers == [LayerEntry(depth=0, note="home.md")]


def test_to_layered_source_not_in_edges_yields_only_source() -> None:
    """If source appears in no edge, only it is in the output."""
    graph = _make_graph({"other.md": [_edge("home.md")]})
    result = to_layered("home.md", graph)
    assert LayerEntry(depth=0, note="home.md") in result.layers


# ---------------------------------------------------------------------------
# Depth 1 — direct forward links
# ---------------------------------------------------------------------------


def test_to_layered_forward_edges_appear_at_depth_one() -> None:
    """Notes directly linked from source appear at depth 1."""
    graph = _make_graph(
        {"home.md": [_edge("about.md"), _edge("tasks.md")]},
        total_files=3,
    )
    result = to_layered("home.md", graph)
    depths = {e.note: e.depth for e in result.layers}
    assert depths["home.md"] == 0
    assert depths["about.md"] == 1
    assert depths["tasks.md"] == 1


def test_to_layered_unresolved_edges_are_ignored() -> None:
    """Unresolved edges contribute no entries to layers."""
    graph = _make_graph(
        {"home.md": [_unresolved_edge("ghost.md")]},
        total_files=1,
    )
    result = to_layered("home.md", graph)
    notes = {e.note for e in result.layers}
    assert "ghost.md" not in notes


# ---------------------------------------------------------------------------
# Depth 1 — backlinks
# ---------------------------------------------------------------------------


def test_to_layered_backlinks_appear_at_depth_one() -> None:
    """A note that links TO source is placed at depth 1 via reverse index."""
    graph = _make_graph(
        {"other.md": [_edge("home.md")]},
        total_files=2,
    )
    result = to_layered("home.md", graph)
    depths = {e.note: e.depth for e in result.layers}
    assert depths["home.md"] == 0
    assert depths["other.md"] == 1


# ---------------------------------------------------------------------------
# Depth 2 — two-hop traversal
# ---------------------------------------------------------------------------


def test_to_layered_two_hop_note_appears_at_depth_two() -> None:
    """A note two hops from source is placed at depth 2."""
    graph = _make_graph(
        {
            "home.md": [_edge("about.md")],
            "about.md": [_edge("projects.md")],
        },
        total_files=3,
    )
    result = to_layered("home.md", graph)
    depths = {e.note: e.depth for e in result.layers}
    assert depths["home.md"] == 0
    assert depths["about.md"] == 1
    assert depths["projects.md"] == 2


# ---------------------------------------------------------------------------
# Shallowest-depth wins
# ---------------------------------------------------------------------------


def test_to_layered_shallowest_depth_wins() -> None:
    """A note reachable at depth 1 and depth 2 appears only at depth 1."""
    # home → about (depth 1) and home → mid → about (depth 2)
    graph = _make_graph(
        {
            "home.md": [_edge("about.md"), _edge("mid.md")],
            "mid.md": [_edge("about.md")],
        },
        total_files=3,
    )
    result = to_layered("home.md", graph)
    about_entries = [e for e in result.layers if e.note == "about.md"]
    assert len(about_entries) == 1
    assert about_entries[0].depth == 1


def test_to_layered_each_note_appears_exactly_once() -> None:
    """Every note in the output appears exactly once regardless of connectivity."""
    graph = _make_graph(
        {
            "home.md": [_edge("a.md"), _edge("b.md")],
            "a.md": [_edge("b.md")],
            "b.md": [_edge("home.md")],
        },
        total_files=3,
    )
    result = to_layered("home.md", graph)
    notes = [e.note for e in result.layers]
    assert len(notes) == len(set(notes))


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_to_layered_layers_are_ordered_by_depth() -> None:
    """Entries are emitted in non-decreasing depth order (BFS guarantee)."""
    graph = _make_graph(
        {
            "home.md": [_edge("about.md")],
            "about.md": [_edge("deep.md")],
        },
        total_files=3,
    )
    result = to_layered("home.md", graph)
    depths = [e.depth for e in result.layers]
    assert depths == sorted(depths)
