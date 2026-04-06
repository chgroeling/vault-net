"""Unit tests for link resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest

from link_tracer.api import (
    _resolve_link_to_file,
    build_vault_context,
    resolve_links,
    scan_vault,
)
from link_tracer.models import ResolveOptions, VaultIndex, _build_vault_lookups


@dataclass
class _FakeFileStats:
    file_size: int = 100
    modified_time: float = 1700000000.0
    access_time: float = 1700000000.0


@dataclass
class _FakeFileEntry:
    file_path: str = "note.md"
    frontmatter: dict = field(default_factory=dict)
    status: str = "ok"
    error: str | None = None
    stats: _FakeFileStats | None = field(default_factory=_FakeFileStats)
    file_hash: str | None = None


@dataclass
class _FakeScanMetadata:
    source_directory: Path = Path("/tmp/vault")  # noqa: S108


@dataclass
class _FakeAggregatedResult:
    metadata: _FakeScanMetadata = field(default_factory=_FakeScanMetadata)
    files: list[_FakeFileEntry] = field(default_factory=list)


def _make_vault_index(
    vault_root: Path = Path("/tmp/vault"),  # noqa: S108
    files: list | None = None,
    source_directory: str = "/tmp/vault",  # noqa: S108
) -> VaultIndex:
    """Construct a minimal VaultIndex for testing."""
    vault_files = [Path(f.file_path) for f in files] if files else []
    name_to_file, stem_to_file, relative_path_to_file = _build_vault_lookups(vault_files)
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
        _FakeFileEntry(file_path="docs/about.md"),
        _FakeFileEntry(file_path="teams/about.md"),
    ]
    vault_index = _make_vault_index(files=files)

    matched = _resolve_link_to_file(Path("about"), vault_index)

    assert matched == Path("docs/about.md")


def test_resolve_link_with_extension_returns_first_duplicate_match() -> None:
    """Unqualified links with extension resolve to the first duplicate match."""
    files = [
        _FakeFileEntry(file_path="docs/about.md"),
        _FakeFileEntry(file_path="teams/about.md"),
    ]
    vault_index = _make_vault_index(files=files)

    matched = _resolve_link_to_file(Path("about.md"), vault_index)

    assert matched == Path("docs/about.md")


def test_resolve_link_uses_path_component_to_disambiguate() -> None:
    """Path-qualified links resolve the matching duplicate file."""
    files = [
        _FakeFileEntry(file_path="docs/about.md"),
        _FakeFileEntry(file_path="teams/about.md"),
    ]
    vault_index = _make_vault_index(files=files)

    matched = _resolve_link_to_file(Path("teams/about"), vault_index)

    assert matched == Path("teams/about.md")


def test_build_vault_context_constructs_from_scan_result() -> None:
    """build_vault_context() creates VaultIndex with lookup maps from scan result."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    files = [
        _FakeFileEntry(file_path="home.md", frontmatter={"title": "Home"}),
        _FakeFileEntry(file_path="about.md", frontmatter={"title": "About"}),
    ]
    scan_result = _FakeAggregatedResult(
        metadata=_FakeScanMetadata(source_directory=vault_root),
        files=files,
    )

    vault_index = build_vault_context(vault_root, scan_result)

    assert vault_index.vault_root == vault_root
    assert vault_index.source_directory == str(vault_root)
    assert len(vault_index.files) == 2
    assert "home.md" in vault_index.name_to_file
    assert "home" in vault_index.stem_to_file
    assert "home.md" in vault_index.relative_path_to_file


def test_scan_vault_delegates_to_scan_directory() -> None:
    """scan_vault() calls scan_directory() and returns VaultIndex."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    fake_files = [
        _FakeFileEntry(file_path="note.md"),
    ]
    fake_result = _FakeAggregatedResult(
        metadata=_FakeScanMetadata(source_directory=vault_root),
        files=fake_files,
    )

    with patch("link_tracer.api.scan_directory", return_value=fake_result):
        vault_index = scan_vault(vault_root)

    assert isinstance(vault_index, VaultIndex)
    assert vault_index.vault_root == vault_root
    assert len(vault_index.files) == 1


def test_resolve_links_uses_prebuilt_index() -> None:
    """resolve_links() works with a prebuilt VaultIndex without scanning."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    note_path = vault_root / "home.md"
    files = [
        _FakeFileEntry(file_path="home.md", frontmatter={"title": "Home"}),
        _FakeFileEntry(file_path="about.md", frontmatter={"title": "About"}),
    ]
    scan_result = _FakeAggregatedResult(
        metadata=_FakeScanMetadata(source_directory=vault_root),
        files=files,
    )
    vault_index = build_vault_context(vault_root, scan_result)

    with patch.object(Path, "read_text", return_value="[[about]]"):
        response = resolve_links(note_path, vault_index)

    assert response.vault_root == str(vault_root)
    assert len(response.matched_links) == 1
    assert any("about.md" in link for link in response.matched_links)


def test_resolve_links_multiple_calls_reuse_same_index() -> None:
    """Multiple resolve_links() calls with same index do not trigger rescanning."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    files = [
        _FakeFileEntry(file_path="home.md", frontmatter={"title": "Home"}),
        _FakeFileEntry(file_path="about.md", frontmatter={"title": "About"}),
        _FakeFileEntry(file_path="contact.md", frontmatter={"title": "Contact"}),
    ]
    scan_result = _FakeAggregatedResult(
        metadata=_FakeScanMetadata(source_directory=vault_root),
        files=files,
    )
    vault_index = build_vault_context(vault_root, scan_result)

    with (
        patch("link_tracer.api.scan_directory") as mock_scan,
        patch.object(Path, "read_text", return_value="[[about]]"),
    ):
        resolve_links(vault_root / "home.md", vault_index)
        resolve_links(vault_root / "about.md", vault_index)

    mock_scan.assert_not_called()


def test_resolve_options_rejects_negative_depth() -> None:
    """ResolveOptions raises ValueError for depth < 0."""
    with pytest.raises(ValueError, match="depth must be >= 0"):
        ResolveOptions(depth=-1)


def test_resolve_links_depth_zero_returns_source_only(tmp_path: Path) -> None:
    """depth=0 returns only the source note with no matched links."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[contact]]", encoding="utf-8")
    (vault_root / "contact.md").write_text("---\ntitle: Contact\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = resolve_links(vault_root / "home.md", vault_index, options=ResolveOptions(depth=0))

    assert len(response.files) == 1
    assert "home.md" in response.files[0].file_path
    assert response.matched_links == []


def test_resolve_links_depth_one_returns_direct_links(tmp_path: Path) -> None:
    """depth=1 returns source note and its direct link targets."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[contact]]", encoding="utf-8")
    (vault_root / "contact.md").write_text("---\ntitle: Contact\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = resolve_links(vault_root / "home.md", vault_index, options=ResolveOptions(depth=1))

    assert len(response.files) == 2
    assert len(response.matched_links) == 1
    assert any("about.md" in link for link in response.matched_links)


def test_resolve_links_depth_two_returns_children_links(tmp_path: Path) -> None:
    """depth=2 returns source, direct links, and links from children."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[contact]]", encoding="utf-8")
    (vault_root / "contact.md").write_text(
        "---\ntitle: Contact\n---\n[[archive]]", encoding="utf-8"
    )
    (vault_root / "archive.md").write_text("---\ntitle: Archive\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = resolve_links(vault_root / "home.md", vault_index, options=ResolveOptions(depth=2))

    assert len(response.files) == 3
    assert len(response.matched_links) == 2
    assert any("about.md" in link for link in response.matched_links)
    assert any("contact.md" in link for link in response.matched_links)


def test_resolve_links_depth_three_returns_grandchildren_links(tmp_path: Path) -> None:
    """depth=3 traverses three levels deep."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\n[[c]]", encoding="utf-8")
    (vault_root / "c.md").write_text("---\ntitle: C\n---\n[[d]]", encoding="utf-8")
    (vault_root / "d.md").write_text("---\ntitle: D\n---\n[[e]]", encoding="utf-8")
    (vault_root / "e.md").write_text("---\ntitle: E\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = resolve_links(vault_root / "a.md", vault_index, options=ResolveOptions(depth=3))

    assert len(response.files) == 4
    assert len(response.matched_links) == 3


def test_resolve_links_circular_links_no_infinite_loop(tmp_path: Path) -> None:
    """Circular links (A->B->A) do not cause infinite loop."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\n[[a]]", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    response = resolve_links(vault_root / "a.md", vault_index, options=ResolveOptions(depth=5))

    assert len(response.files) == 2
    assert len(response.matched_links) == 1


def test_resolve_links_default_depth_is_one() -> None:
    """Default ResolveOptions uses depth=1."""
    options = ResolveOptions()
    assert options.depth == 1
