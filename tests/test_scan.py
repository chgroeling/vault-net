"""Unit tests for the scan module (scan_vault)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from link_tracer import scan_vault
from link_tracer.models import VaultIndex
from tests.fixtures import FakeFileEntry, FakeScanMetadata, FakeScanResults


def test_scan_vault_delegates_to_scan_directory() -> None:
    """scan_vault() calls scan_directory() and returns VaultIndex."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    fake_files = [
        FakeFileEntry(file_path="note.md"),
    ]
    fake_result = FakeScanResults(
        metadata=FakeScanMetadata(root=str(vault_root)),
        files=fake_files,
    )

    with patch("link_tracer.scan.scan_directory", return_value=fake_result) as mock_scan:
        vault_index = scan_vault(vault_root)

    assert isinstance(vault_index, VaultIndex)
    assert vault_index.vault_root == vault_root
    assert len(vault_index.files) == 1
    callback = mock_scan.call_args.kwargs.get("callback")
    assert callable(callback)
