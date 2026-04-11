"""Domain service tests for registry lookup behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from vault_net.domain.services.vault_registry import VaultRegistry
from vault_net.infrastructure.scanner.matterify_scanner import MatterifyVaultScanner


@pytest.fixture
def simple_vault(tmp_path: Path) -> tuple[Path, VaultRegistry]:
    """Create a simple vault with basic files for testing."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("", encoding="utf-8")
    (vault_root / "about.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    vault_index = scanner.scan(vault_root)
    return vault_root, VaultRegistry(vault_index)


@pytest.fixture
def structured_vault(tmp_path: Path) -> tuple[Path, Path, VaultRegistry]:
    """Create a vault with subdirectory structure for testing nested paths."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    subdir = vault_root / "3_structs"
    subdir.mkdir()
    (vault_root / "home.md").write_text("", encoding="utf-8")
    (vault_root / "about.md").write_text("", encoding="utf-8")
    (subdir / "Die drei ethischen Regeln.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    vault_index = scanner.scan(vault_root)
    return vault_root, subdir, VaultRegistry(vault_index)


def test_vault_registry_provides_bidirectional_lookup(tmp_path: Path) -> None:
    """Registry resolves both slug->file and file->slug lookups."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    vault_index = scanner.scan(vault_root)
    lookup = VaultRegistry(vault_index)
    home_note = vault_index.files[0]

    assert lookup.get_file(home_note.slug) == home_note
    assert lookup.get_slug(home_note) == home_note.slug
    assert lookup.get_file("missing") is None
    assert lookup.get_slug(home_note.to_file()) == home_note.slug


def test_get_slug_by_path_returns_slug_for_existing_file(
    simple_vault: tuple[Path, VaultRegistry],
) -> None:
    """get_slug_by_path returns slug when file_path matches."""
    _, registry = simple_vault
    result = registry.get_slug_by_path("home.md")
    assert result == "home.md"


def test_get_slug_by_path_returns_none_for_missing_file(
    simple_vault: tuple[Path, VaultRegistry],
) -> None:
    """get_slug_by_path returns None when file_path not found."""
    _, registry = simple_vault
    assert registry.get_slug_by_path("nonexistent.md") is None


def test_get_slug_by_path_returns_none_for_partial_path(
    structured_vault: tuple[Path, Path, VaultRegistry],
) -> None:
    """get_slug_by_path does not do partial matching."""
    _, _, registry = structured_vault
    assert registry.get_slug_by_path("3_structs") is None
    assert registry.get_slug_by_path("Die drei") is None


def test_resolve_to_slug_by_direct_slug(simple_vault: tuple[Path, VaultRegistry]) -> None:
    """resolve_to_slug returns slug when input is a direct slug match."""
    _, registry = simple_vault
    result = registry.resolve_to_slug("home.md", Path("/fake/vault"))
    assert result == "home.md"


def test_resolve_to_slug_by_relative_path(simple_vault: tuple[Path, VaultRegistry]) -> None:
    """resolve_to_slug resolves relative path to slug."""
    vault_root, registry = simple_vault
    result = registry.resolve_to_slug("about.md", vault_root)
    assert result == "about.md"


def test_resolve_to_slug_by_nested_relative_path(
    structured_vault: tuple[Path, Path, VaultRegistry],
) -> None:
    """resolve_to_slug resolves nested relative path to slug."""
    vault_root, _, registry = structured_vault
    result = registry.resolve_to_slug("3_structs/Die drei ethischen Regeln.md", vault_root)
    assert result == "Die-drei"


def test_resolve_to_slug_by_absolute_path(
    structured_vault: tuple[Path, Path, VaultRegistry],
) -> None:
    """resolve_to_slug resolves absolute path to slug."""
    vault_root, subdir, registry = structured_vault
    note_path = subdir / "Die drei ethischen Regeln.md"
    result = registry.resolve_to_slug(str(note_path), vault_root)
    assert result == "Die-drei"


def test_resolve_to_slug_returns_none_for_missing_input(
    simple_vault: tuple[Path, VaultRegistry],
) -> None:
    """resolve_to_slug returns None when input cannot be resolved."""
    vault_root, registry = simple_vault
    assert registry.resolve_to_slug("missing.md", vault_root) is None
    assert registry.resolve_to_slug("missing/slug.md", vault_root) is None


def test_resolve_to_slug_returns_none_for_path_not_in_vault(
    tmp_path: Path,
) -> None:
    """resolve_to_slug returns None when absolute path is outside vault."""
    outside_vault = tmp_path / "outside.md"
    outside_vault.write_text("", encoding="utf-8")
    other_vault = tmp_path / "other_vault"
    other_vault.mkdir()
    (other_vault / "home.md").write_text("", encoding="utf-8")

    scanner = MatterifyVaultScanner()
    vault_index = scanner.scan(other_vault)
    registry = VaultRegistry(vault_index)

    assert registry.resolve_to_slug(str(outside_vault), other_vault) is None
