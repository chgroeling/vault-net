"""Unit tests for link resolution helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from link_tracer.api import _build_vault_lookups, _resolve_link_to_file


def test_resolve_link_returns_first_match_for_duplicate_names() -> None:
    """Unqualified links resolve to the first matching file when duplicates exist."""
    vault_files = [Path("docs/about.md"), Path("teams/about.md")]
    name_to_file, stem_to_file, relative_path_to_file = _build_vault_lookups(vault_files)

    matched = _resolve_link_to_file(
        Path("about"),
        name_to_file,
        stem_to_file,
        relative_path_to_file,
    )

    assert matched == Path("docs/about.md")


def test_resolve_link_with_extension_returns_first_duplicate_match() -> None:
    """Unqualified links with extension resolve to the first duplicate match."""
    vault_files = [Path("docs/about.md"), Path("teams/about.md")]
    name_to_file, stem_to_file, relative_path_to_file = _build_vault_lookups(vault_files)

    matched = _resolve_link_to_file(
        Path("about.md"),
        name_to_file,
        stem_to_file,
        relative_path_to_file,
    )

    assert matched == Path("docs/about.md")


def test_resolve_link_uses_path_component_to_disambiguate() -> None:
    """Path-qualified links resolve the matching duplicate file."""
    vault_files = [Path("docs/about.md"), Path("teams/about.md")]
    name_to_file, stem_to_file, relative_path_to_file = _build_vault_lookups(vault_files)

    matched = _resolve_link_to_file(
        Path("teams/about"),
        name_to_file,
        stem_to_file,
        relative_path_to_file,
    )

    assert matched == Path("teams/about.md")


def test_trace_links_defaults_no_options() -> None:
    """trace_links() works with default options."""
    from link_tracer.api import trace_links

    vault = Path("/tmp/fake-vault")  # noqa: S108
    note = vault / "note.md"

    with (
        patch("link_tracer.api.scan_directory") as mock_scan,
        patch.object(Path, "read_text", return_value="[[other]]"),
    ):
        mock_scan.return_value.metadata.source_directory = vault
        mock_scan.return_value.files = []

        trace_links(note, vault)
        mock_scan.assert_called_once_with(vault)
