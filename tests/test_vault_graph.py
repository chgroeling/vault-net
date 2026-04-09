"""Unit tests for the vault_graph module."""

from __future__ import annotations

from pathlib import Path

from vault_net import build_vault_graph, scan_vault


def test_build_vault_graph_returns_first_match_for_duplicate_names(tmp_path: Path) -> None:
    """Unqualified links resolve to the first matching file when duplicates exist."""
    vault_root = tmp_path / "vault"
    (vault_root / "docs").mkdir(parents=True)
    (vault_root / "teams").mkdir()
    (vault_root / "source.md").write_text("[[about]]", encoding="utf-8")
    (vault_root / "docs" / "about.md").write_text("", encoding="utf-8")
    (vault_root / "teams" / "about.md").write_text("", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = build_vault_graph(vault_index)

    assert response.edges["source.md"][0].resolved is True
    assert response.edges["source.md"][0].target_note == "docs/about.md"


def test_build_vault_graph_with_extension_returns_first_duplicate_match(tmp_path: Path) -> None:
    """Unqualified links with extension resolve to the first duplicate match."""
    vault_root = tmp_path / "vault"
    (vault_root / "docs").mkdir(parents=True)
    (vault_root / "teams").mkdir()
    (vault_root / "source.md").write_text("[[about.md]]", encoding="utf-8")
    (vault_root / "docs" / "about.md").write_text("", encoding="utf-8")
    (vault_root / "teams" / "about.md").write_text("", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = build_vault_graph(vault_index)

    assert response.edges["source.md"][0].resolved is True
    assert response.edges["source.md"][0].target_note == "docs/about.md"


def test_build_vault_graph_uses_path_component_to_disambiguate(tmp_path: Path) -> None:
    """Path-qualified links resolve the matching duplicate file."""
    vault_root = tmp_path / "vault"
    (vault_root / "docs").mkdir(parents=True)
    (vault_root / "teams").mkdir()
    (vault_root / "source.md").write_text("[[teams/about]]", encoding="utf-8")
    (vault_root / "docs" / "about.md").write_text("", encoding="utf-8")
    (vault_root / "teams" / "about.md").write_text("", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = build_vault_graph(vault_index)

    assert response.edges["source.md"][0].resolved is True
    assert response.edges["source.md"][0].target_note == "teams/about.md"


def test_build_vault_graph_resolves_edges_for_every_file(tmp_path: Path) -> None:
    """resolve_vault_links() builds edges for all notes in the scanned vault."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[missing]]", encoding="utf-8")
    (vault_root / "tasks.md").write_text("---\ntitle: Tasks\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = build_vault_graph(vault_index)

    assert response.vault_root == str(vault_root)
    assert response.metadata.total_files == 3
    assert set(response.edges) == {"home.md", "about.md"}
    assert response.edges["home.md"][0].resolved is True
    assert response.edges["home.md"][0].target_note == "about.md"
    assert response.edges["about.md"][0].resolved is False
    assert response.edges["about.md"][0].unresolved_reason == "not_found"
