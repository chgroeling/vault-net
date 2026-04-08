"""Unit tests for the resolve_vault_links module."""

from __future__ import annotations

from pathlib import Path

from link_tracer import resolve_vault_links, scan_vault
from link_tracer.models import VaultIndex
from link_tracer.resolve_vault_links import _resolve_link_to_file
from tests.fixtures import FakeFileEntry


def _make_vault_index(
    vault_root: Path = Path("/tmp/vault"),  # noqa: S108
    files: list | None = None,
    source_directory: str = "/tmp/vault",  # noqa: S108
) -> VaultIndex:
    """Construct a minimal VaultIndex for testing."""
    vault_files = [Path(f.file_path) for f in files] if files else []
    name_to_file, stem_to_file, relative_path_to_file = VaultIndex._build_vault_lookups(vault_files)
    return VaultIndex(
        vault_root=vault_root,
        files=files or [],
        source_directory=source_directory,
        name_to_file=name_to_file,
        stem_to_file=stem_to_file,
        relative_path_to_file=relative_path_to_file,
    )


def test_resolve_link_returns_first_match_for_duplicate_names() -> None:
    """Unqualified links resolve to the first matching file when duplicates exist."""
    files = [
        FakeFileEntry(file_path="docs/about.md"),
        FakeFileEntry(file_path="teams/about.md"),
    ]
    vault_index = _make_vault_index(files=files)

    matched = _resolve_link_to_file(Path("about"), vault_index)

    assert matched == Path("docs/about.md")


def test_resolve_link_with_extension_returns_first_duplicate_match() -> None:
    """Unqualified links with extension resolve to the first duplicate match."""
    files = [
        FakeFileEntry(file_path="docs/about.md"),
        FakeFileEntry(file_path="teams/about.md"),
    ]
    vault_index = _make_vault_index(files=files)

    matched = _resolve_link_to_file(Path("about.md"), vault_index)

    assert matched == Path("docs/about.md")


def test_resolve_link_uses_path_component_to_disambiguate() -> None:
    """Path-qualified links resolve the matching duplicate file."""
    files = [
        FakeFileEntry(file_path="docs/about.md"),
        FakeFileEntry(file_path="teams/about.md"),
    ]
    vault_index = _make_vault_index(files=files)

    matched = _resolve_link_to_file(Path("teams/about"), vault_index)

    assert matched == Path("teams/about.md")


def test_resolve_vault_links_resolves_edges_for_every_file(tmp_path: Path) -> None:
    """resolve_vault_links() builds edges for all notes in the scanned vault."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[missing]]", encoding="utf-8")
    (vault_root / "tasks.md").write_text("---\ntitle: Tasks\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = resolve_vault_links(vault_index)

    assert response.vault_root == str(vault_root)
    assert response.metadata.total_files == 3
    assert set(response.edges) == {"home.md", "about.md"}
    assert response.edges["home.md"][0].resolved is True
    assert response.edges["home.md"][0].target_note == "about.md"
    assert response.edges["about.md"][0].resolved is False
    assert response.edges["about.md"][0].unresolved_reason == "not_found"
