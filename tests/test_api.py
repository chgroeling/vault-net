"""Unit tests for link resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest

from link_tracer.api import (
    _resolve_link_to_file,
    build_index,
    resolve_links,
    resolve_vault_links,
    scan_vault,
)
from link_tracer.models import ResolveOptions, VaultIndex


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


def test_build_vault_graph_constructs_from_scan_result() -> None:
    """build_vault_graph() creates VaultIndex with lookup maps from scan result."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    files = [
        _FakeFileEntry(file_path="home.md", frontmatter={"title": "Home"}),
        _FakeFileEntry(file_path="about.md", frontmatter={"title": "About"}),
    ]
    scan_result = _FakeAggregatedResult(
        metadata=_FakeScanMetadata(source_directory=vault_root),
        files=files,
    )

    vault_index = build_index(vault_root, scan_result)

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

    with patch("link_tracer.api.scan_directory", return_value=fake_result) as mock_scan:
        vault_index = scan_vault(vault_root)

    assert isinstance(vault_index, VaultIndex)
    assert vault_index.vault_root == vault_root
    assert len(vault_index.files) == 1
    callback = mock_scan.call_args.kwargs.get("callback")
    assert callable(callback)


def test_resolve_links_uses_prebuilt_index() -> None:
    """resolve_links() works with a prebuilt VaultGraph."""
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
    vault_index = build_index(vault_root, scan_result)
    with patch.object(Path, "read_text", return_value="[[about]]"):
        vault_graph = resolve_vault_links(vault_index)

    with patch.object(Path, "read_text", return_value="[[about]]"):
        _, graph = resolve_links(note_path, vault_graph, vault_index)

    assert graph.vault_root == str(vault_root)
    assert set(graph.edges) == {"home.md"}
    assert [edge.target_note for edge in graph.edges["home.md"]] == ["about.md"]
    assert graph.edges["home.md"][0].resolved is True


def test_resolve_links_multiple_calls_reuse_same_index() -> None:
    """Multiple resolve_links() calls with same vault response do not rescan."""
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
    vault_index = build_index(vault_root, scan_result)
    with patch.object(Path, "read_text", return_value="[[about]]"):
        vault_graph = resolve_vault_links(vault_index)

    with (
        patch("link_tracer.api.scan_directory") as mock_scan,
        patch.object(Path, "read_text", return_value="[[about]]"),
    ):
        resolve_links(vault_root / "home.md", vault_graph, vault_index)
        resolve_links(vault_root / "about.md", vault_graph, vault_index)

    mock_scan.assert_not_called()


def test_resolve_options_rejects_negative_depth() -> None:
    """ResolveOptions raises ValueError for depth < 0."""
    with pytest.raises(ValueError, match="depth must be >= 0"):
        ResolveOptions(depth=-1)


def test_resolve_links_depth_zero_returns_source_only(tmp_path: Path) -> None:
    """depth=0 returns only the source note with no edges."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[contact]]", encoding="utf-8")
    (vault_root / "contact.md").write_text("---\ntitle: Contact\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(
        vault_root / "home.md", vault_response, vault_index, options=ResolveOptions(depth=0)
    )

    assert graph.metadata.total_files == 1
    assert graph.edges == {}


def test_resolve_links_depth_one_returns_direct_links(tmp_path: Path) -> None:
    """depth=1 returns source note and direct outgoing link edges."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[contact]]", encoding="utf-8")
    (vault_root / "contact.md").write_text("---\ntitle: Contact\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(
        vault_root / "home.md", vault_response, vault_index, options=ResolveOptions(depth=1)
    )

    assert graph.metadata.total_files == 2
    assert set(graph.edges) == {"home.md"}
    assert [edge.target_note for edge in graph.edges["home.md"]] == ["about.md"]


def test_resolve_links_uses_indexed_links_without_file_reads(tmp_path: Path) -> None:
    """resolve_links() uses indexed link payloads when available."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)

    with patch.object(Path, "read_text", side_effect=AssertionError("unexpected file read")):
        _, graph = resolve_links(
            vault_root / "home.md", vault_response, vault_index, options=ResolveOptions(depth=1)
        )

    assert set(graph.edges) == {"home.md"}
    assert [edge.target_note for edge in graph.edges["home.md"]] == ["about.md"]


def test_resolve_links_depth_two_returns_children_links(tmp_path: Path) -> None:
    """depth=2 returns outgoing edges for source and first-level children."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text("---\ntitle: Home\n---\n[[about]]", encoding="utf-8")
    (vault_root / "about.md").write_text("---\ntitle: About\n---\n[[contact]]", encoding="utf-8")
    (vault_root / "contact.md").write_text(
        "---\ntitle: Contact\n---\n[[archive]]", encoding="utf-8"
    )
    (vault_root / "archive.md").write_text("---\ntitle: Archive\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(
        vault_root / "home.md", vault_response, vault_index, options=ResolveOptions(depth=2)
    )

    assert graph.metadata.total_files == 3
    assert set(graph.edges) == {"home.md", "about.md"}
    assert [edge.target_note for edge in graph.edges["home.md"]] == ["about.md"]
    assert [edge.target_note for edge in graph.edges["about.md"]] == ["contact.md"]


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
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "a.md", vault_response, vault_index, options=ResolveOptions(depth=3))

    assert graph.metadata.total_files == 4
    assert set(graph.edges) == {"a.md", "b.md", "c.md"}


def test_resolve_links_circular_links_no_infinite_loop(tmp_path: Path) -> None:
    """Circular links (A->B->A) do not cause infinite loop."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\n[[a]]", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "a.md", vault_response, vault_index, options=ResolveOptions(depth=5))

    assert graph.metadata.total_files == 2
    assert set(graph.edges) == {"a.md", "b.md"}
    assert [edge.target_note for edge in graph.edges["a.md"]] == ["b.md"]
    assert [edge.target_note for edge in graph.edges["b.md"]] == ["a.md"]


def test_resolve_links_includes_unresolved_edges(tmp_path: Path) -> None:
    """Unresolvable file links are reported as unresolved edges."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "home.md").write_text(
        "---\ntitle: Home\n---\n[[about]] and [[missing-note]]", encoding="utf-8"
    )
    (vault_root / "about.md").write_text("---\ntitle: About\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(
        vault_root / "home.md", vault_response, vault_index, options=ResolveOptions(depth=1)
    )

    assert set(graph.edges) == {"home.md"}
    assert graph.edges["home.md"][0].resolved is True
    assert graph.edges["home.md"][0].target_note == "about.md"
    assert graph.edges["home.md"][0].link.target == "about"
    assert graph.edges["home.md"][1].resolved is False
    assert graph.edges["home.md"][1].target_note is None
    assert graph.edges["home.md"][1].unresolved_reason == "not_found"
    assert graph.edges["home.md"][1].link.target == "missing-note"


def test_resolve_links_external_note_outside_vault_uses_fallback_parsing(tmp_path: Path) -> None:
    """External source note still resolves links via fallback parsing."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "about.md").write_text("---\ntitle: About\n---\nNo links", encoding="utf-8")

    external_root = tmp_path / "external"
    external_root.mkdir()
    external_note = external_root / "outside.md"
    external_note.write_text("[[about]] and [[missing-note]]", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    source_note, graph = resolve_links(external_note, vault_response, vault_index, options=ResolveOptions(depth=1))

    source_key = str(external_note.resolve())
    assert source_note == source_key
    assert set(graph.edges) == {source_key}
    assert graph.edges[source_key][0].resolved is True
    assert graph.edges[source_key][0].target_note == "about.md"
    assert graph.edges[source_key][1].resolved is False
    assert graph.edges[source_key][1].target_note is None
    assert graph.edges[source_key][1].unresolved_reason == "not_found"


def test_resolve_links_default_depth_is_one() -> None:
    """Default ResolveOptions uses depth=1."""
    options = ResolveOptions()
    assert options.depth == 1


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


# --- Backlink tests ---


def test_backlinks_depth_one_shows_incoming_edges(tmp_path: Path) -> None:
    """depth=1 includes backlink edges from notes that link to the source."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "b.md", vault_response, vault_index, options=ResolveOptions(depth=1))

    # b.md has no forward edges, but a.md links to b.md → backlink
    assert "a.md" in graph.edges
    backlink_edges = graph.edges["a.md"]
    assert len(backlink_edges) == 1
    assert backlink_edges[0].target_note == "b.md"
    assert backlink_edges[0].resolved is True


def test_backlinks_depth_two_bidirectional(tmp_path: Path) -> None:
    """depth=2 traverses forward and backward across two levels."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\n[[c]]", encoding="utf-8")
    (vault_root / "c.md").write_text("---\ntitle: C\n---\nNo links", encoding="utf-8")
    (vault_root / "d.md").write_text("---\ntitle: D\n---\n[[a]]", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "b.md", vault_response, vault_index, options=ResolveOptions(depth=2))

    # depth=1 from b: forward→c, backlink a→b
    # depth=2 from c: no forward, no backlinks besides b→c (already visited)
    # depth=2 from a: forward a→b (already visited), backlink d→a
    assert "b.md" in graph.edges  # forward b→c
    assert "a.md" in graph.edges  # a→b (backlink at depth=1, forward at depth=2)
    assert "d.md" in graph.edges  # d→a (backlink at depth=2)

    assert any(e.target_note == "c.md" for e in graph.edges["b.md"])
    assert any(e.target_note == "b.md" for e in graph.edges["a.md"])
    assert any(e.target_note == "a.md" for e in graph.edges["d.md"])


def test_backlink_no_duplicate_when_forward_visited(tmp_path: Path) -> None:
    """A backlink edge is not duplicated when the source is also forward-visited."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    # a→b and b→a: circular. Resolve a at depth=2.
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\n[[a]]", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "a.md", vault_response, vault_index, options=ResolveOptions(depth=2))

    # a.md should have exactly one edge a→b (no duplicate from backlink discovery)
    assert len(graph.edges.get("a.md", [])) == 1
    assert graph.edges["a.md"][0].target_note == "b.md"

    # b.md should have exactly one edge b→a
    assert len(graph.edges.get("b.md", [])) == 1
    assert graph.edges["b.md"][0].target_note == "a.md"


def test_no_backlinks_for_isolated_note(tmp_path: Path) -> None:
    """A note with no incoming links has no backlink edges."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\nNo links", encoding="utf-8")
    (vault_root / "c.md").write_text("---\ntitle: C\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    # Resolve a.md — nobody links to a.md, so no backlinks
    _, graph = resolve_links(vault_root / "a.md", vault_response, vault_index, options=ResolveOptions(depth=1))

    assert set(graph.edges) == {"a.md"}
    assert all(e.resolved for e in graph.edges["a.md"])


def test_backlink_circular_links_no_infinite_loop(tmp_path: Path) -> None:
    """Circular links with backlinks do not cause infinite loop."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\n[[a]]", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "a.md", vault_response, vault_index, options=ResolveOptions(depth=5))

    assert graph.metadata.total_files == 2
    assert "a.md" in graph.edges
    assert "b.md" in graph.edges


def test_backlinks_depth_zero_no_edges(tmp_path: Path) -> None:
    """depth=0 returns no edges even when backlinks exist."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "a.md").write_text("---\ntitle: A\n---\n[[b]]", encoding="utf-8")
    (vault_root / "b.md").write_text("---\ntitle: B\n---\nNo links", encoding="utf-8")

    vault_index = scan_vault(vault_root)
    vault_response = resolve_vault_links(vault_index)
    _, graph = resolve_links(vault_root / "b.md", vault_response, vault_index, options=ResolveOptions(depth=0))

    assert graph.edges == {}
    assert graph.metadata.total_files == 1
