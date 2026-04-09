"""Unit tests for the scan module (scan_vault)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from obsilink import Link, LinkType

from tests.fixtures import FakeFileEntry, FakeScanMetadata, FakeScanResults
from vault_net import scan_vault
from vault_net.models import VaultIndex


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

    with patch("vault_net.scan.scan_directory", return_value=fake_result) as mock_scan:
        vault_index = scan_vault(vault_root)

    assert isinstance(vault_index, VaultIndex)
    assert vault_index.vault_root == vault_root
    assert len(vault_index.files) == 1
    callback = mock_scan.call_args.kwargs.get("callback")
    assert callable(callback)


def test_scan_vault_converts_custom_data_to_vault_links() -> None:
    """scan_vault() converts matterify custom_data Link objects into VaultLink objects."""
    vault_root = Path("/tmp/vault")  # noqa: S108
    fake_files = [
        FakeFileEntry(
            file_path="note.md",
            custom_data=[
                Link(
                    type=LinkType.WIKILINK,
                    target="other",
                    alias=None,
                    heading="Section",
                    blockid=None,
                ),
            ],
        ),
    ]
    fake_result = FakeScanResults(
        metadata=FakeScanMetadata(root=str(vault_root)),
        files=fake_files,
    )

    with patch("vault_net.scan.scan_directory", return_value=fake_result):
        vault_index = scan_vault(vault_root)

    assert vault_index.files[0].links is not None
    assert len(vault_index.files[0].links) == 1
    link = vault_index.files[0].links[0]
    assert link.link_type == "wikilink"
    assert link.target == "other"
    assert link.heading == "Section"


def test_scan_vault_slug_collision_with_reserved_name() -> None:
    """Test slug generation when two files collide and a third has the reserved name.

    When two files have the same first SLUG_LENGTH characters, the second gets _0 suffix.
    If a third file would naturally have that _0 suffix, it should get _1 instead.
    """
    vault_root = Path("/tmp/vault")  # noqa: S108
    # All have "longname" as first 8 chars of filename
    # "longname.md" -> "longname"
    # "longname.txt" -> "longname" (collision, gets "longname_0")
    # "longname_0.md" -> "longname" (collision, "longname_0" taken, gets "longname_1")
    fake_files = [
        FakeFileEntry(file_path="folder1/longname.md"),
        FakeFileEntry(file_path="folder2/longname.txt"),
        FakeFileEntry(file_path="folder3/longname_0.md"),
    ]
    fake_result = FakeScanResults(
        metadata=FakeScanMetadata(root=str(vault_root)),
        files=fake_files,
    )

    with patch("vault_net.scan.scan_directory", return_value=fake_result):
        vault_index = scan_vault(vault_root)

    slugs = {f.file_path: f.slug for f in vault_index.files}
    assert slugs["folder1/longname.md"] == "longname"
    assert slugs["folder2/longname.txt"] == "longname_0"
    assert slugs["folder3/longname_0.md"] == "longname_1"
