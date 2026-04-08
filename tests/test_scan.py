"""Unit tests for the scan module (build_index, scan_vault)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from link_tracer import build_index, scan_vault
from link_tracer.models import VaultIndex
from tests.fixtures import FakeAggregatedResult, FakeFileEntry, FakeScanMetadata


def test_build_vault_graph_constructs_from_scan_result() -> None:
    """build_index() creates VaultIndex with lookup maps from scan result."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    files = [
        FakeFileEntry(file_path="home.md", frontmatter={"title": "Home"}),
        FakeFileEntry(file_path="about.md", frontmatter={"title": "About"}),
    ]
    scan_result = FakeAggregatedResult(
        metadata=FakeScanMetadata(source_directory=vault_root),
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
        FakeFileEntry(file_path="note.md"),
    ]
    fake_result = FakeAggregatedResult(
        metadata=FakeScanMetadata(source_directory=vault_root),
        files=fake_files,
    )

    with patch("link_tracer.scan.scan_directory", return_value=fake_result) as mock_scan:
        vault_index = scan_vault(vault_root)

    assert isinstance(vault_index, VaultIndex)
    assert vault_index.vault_root == vault_root
    assert len(vault_index.files) == 1
    callback = mock_scan.call_args.kwargs.get("callback")
    assert callable(callback)
