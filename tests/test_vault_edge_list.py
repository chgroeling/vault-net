"""Unit tests for the vault_edge_list module."""

from __future__ import annotations

from pathlib import Path

from vault_net import build_vault_edge_list, scan_vault


def test_build_vault_edge_list_resolves_to_slug_pairs(tmp_path: Path) -> None:
    """Return resolved edges as source/target slug pairs."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("[[about]]\n[[missing]]\n", encoding="utf-8")
    (vault_root / "about.md").write_text("", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    edge_list = build_vault_edge_list(vault_index)

    assert edge_list == [["home.md", "about.md"]]


def test_build_vault_edge_list_deduplicates_edges(tmp_path: Path) -> None:
    """Collapse repeated links to a single edge pair."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("[[about]]\n[[about]]\n[[about.md]]\n", encoding="utf-8")
    (vault_root / "about.md").write_text("", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    edge_list = build_vault_edge_list(vault_index)

    assert edge_list == [["home.md", "about.md"]]


def test_build_vault_edge_list_skips_self_loop(tmp_path: Path) -> None:
    """Skip resolved self-loop edges from the output."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("[[home]]\n", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    edge_list = build_vault_edge_list(vault_index)

    assert edge_list == []
