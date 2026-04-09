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

    When two files have the same first SLUG_LENGTH characters, the second gets _0 suffix
    shortened to fit within SLUG_LENGTH. If a third file would naturally have that _0
    suffix, it should get _1 instead.
    """
    vault_root = Path("/tmp/vault")  # noqa: S108
    # All have "longname" as first 8 chars of filename
    # "longname.md" -> "longname" (8 chars)
    # "longname.txt" -> "longna_0" (shortened to 6 + 2 = 8 chars)
    # "longname_0.md" -> "longna_1" (collision, "longna_0" taken, gets "longna_1")
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
    assert slugs["folder2/longname.txt"] == "longna_0"
    assert slugs["folder3/longname_0.md"] == "longna_1"


def test_scan_vault_slug_max_length_constraint() -> None:
    """Test that all generated slugs are at most SLUG_LENGTH characters long.

    This verifies that collision suffixes (_N) are accommodated by shortening
    the base name, not by extending beyond SLUG_LENGTH.
    """
    vault_root = Path("/tmp/vault")  # noqa: S108
    from vault_net.consts import SLUG_LENGTH

    # Test files showing various collision scenarios
    fake_files = [
        FakeFileEntry(file_path="longname.md"),  # "longname" (8 chars)
        FakeFileEntry(file_path="longname.txt"),  # "longna_0" (8 chars, shortened)
        FakeFileEntry(file_path="abcdefghijk.md"),  # "abcdefgh" (8 chars, truncated)
        FakeFileEntry(file_path="abcdefghijk.txt"),  # "abcdef_0" (8 chars, shortened)
    ]
    fake_result = FakeScanResults(
        metadata=FakeScanMetadata(root=str(vault_root)),
        files=fake_files,
    )

    with patch("vault_net.scan.scan_directory", return_value=fake_result):
        vault_index = scan_vault(vault_root)

    for file in vault_index.files:
        assert len(file.slug) <= SLUG_LENGTH, (
            f"Slug '{file.slug}' for {file.file_path} exceeds max length {SLUG_LENGTH}"
        )

    slugs = {f.file_path: f.slug for f in vault_index.files}
    assert slugs["longname.md"] == "longname"
    assert slugs["longname.txt"] == "longna_0"
    assert slugs["abcdefghijk.md"] == "abcdefgh"
    assert slugs["abcdefghijk.txt"] == "abcdef_0"


def test_scan_vault_slug_many_collisions() -> None:
    """Test slug generation with 10+ collisions for the same base name.

    Verifies that the algorithm correctly handles double-digit suffixes
    and progressively shortens the base to fit within SLUG_LENGTH.
    """
    vault_root = Path("/tmp/vault")  # noqa: S108
    from vault_net.consts import SLUG_LENGTH

    # Create 12 files with the same first 8 chars "filename"
    fake_files = [FakeFileEntry(file_path=f"folder{i}/filename{i}.txt") for i in range(12)]
    fake_result = FakeScanResults(
        metadata=FakeScanMetadata(root=str(vault_root)),
        files=fake_files,
    )

    with patch("vault_net.scan.scan_directory", return_value=fake_result):
        vault_index = scan_vault(vault_root)

    # Verify all slugs are unique and within length limit
    slugs = [f.slug for f in vault_index.files]
    assert len(slugs) == len(set(slugs)), "All slugs must be unique"

    for slug in slugs:
        assert len(slug) <= SLUG_LENGTH, f"Slug '{slug}' exceeds max length {SLUG_LENGTH}"

    # Slug assignment:
    # folder0/filename0.txt -> "filename" (first, no collision)
    # folder1/filename1.txt -> "filena_0" (collides with "filename", shortens to 6+2=8)
    # folder2/filename2.txt -> "filena_1" (6+2=8)
    # ...
    # folder9/filename9.txt -> "filena_8" (6+2=8)
    # folder10/filename10.txt -> "filena_9" (6+2=8)
    # folder11/filename11.txt -> "filen_10" (5+3=8, shortened more for 3-digit suffix)
    slugs_map = {f.file_path: f.slug for f in vault_index.files}
    assert slugs_map["folder0/filename0.txt"] == "filename"
    assert slugs_map["folder1/filename1.txt"] == "filena_0"
    assert slugs_map["folder9/filename9.txt"] == "filena_8"
    assert slugs_map["folder10/filename10.txt"] == "filena_9"
    assert slugs_map["folder11/filename11.txt"] == "filen_10"
