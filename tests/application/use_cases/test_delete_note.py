"""Tests for DeleteNoteUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vault_net.application.use_cases.delete_note import DeleteNoteUseCase
from vault_net.domain.models import VaultFile, VaultListing


def _make_note(slug: str, file_path: str) -> VaultFile:
    return VaultFile(slug=slug, file_path=file_path)


def _make_use_case(
    notes: list[VaultFile],
    vault_root: Path,
) -> DeleteNoteUseCase:
    listing = VaultListing(vault_root=vault_root, files=notes)
    scanner = MagicMock()
    scanner.index_files.return_value = listing
    return DeleteNoteUseCase(scanner=scanner)


class TestDeleteNoteUseCase:
    """Verify DeleteNoteUseCase behavior."""

    def test_deletes_note_by_slug(self, tmp_path: Path) -> None:
        """Delete a note resolved by slug and return its file path."""
        note_file = tmp_path / "hello.md"
        note_file.write_text("# Hello", encoding="utf-8")
        note = _make_note("HELLO__", "hello.md")

        use_case = _make_use_case([note], tmp_path)
        result = use_case.execute(tmp_path, "HELLO__")

        assert result == "hello.md"
        assert not note_file.exists()

    def test_deletes_note_in_subdirectory(self, tmp_path: Path) -> None:
        """Delete a note inside a subdirectory."""
        sub = tmp_path / "sub" / "dir"
        sub.mkdir(parents=True)
        note_file = sub / "deep.md"
        note_file.write_text("deep content", encoding="utf-8")
        note = _make_note("DEEP__", "sub/dir/deep.md")

        use_case = _make_use_case([note], tmp_path)
        result = use_case.execute(tmp_path, "DEEP__")

        assert result == "sub/dir/deep.md"
        assert not note_file.exists()

    def test_raises_key_error_for_unknown_slug(self, tmp_path: Path) -> None:
        """Raise KeyError when the slug cannot be resolved."""
        use_case = _make_use_case([], tmp_path)

        with pytest.raises(KeyError):
            use_case.execute(tmp_path, "NONEXISTENT")

    def test_raises_file_not_found_when_file_missing(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError when the resolved file doesn't exist on disk."""
        note = _make_note("GONE__", "gone.md")
        use_case = _make_use_case([note], tmp_path)

        with pytest.raises(FileNotFoundError, match="does not exist"):
            use_case.execute(tmp_path, "GONE__")

    def test_passes_exclude_options_to_scanner(self, tmp_path: Path) -> None:
        """Forward extra_exclude and no_default_excludes to the scanner."""
        note_file = tmp_path / "note.md"
        note_file.write_text("", encoding="utf-8")
        note = _make_note("NOTE__", "note.md")

        use_case = _make_use_case([note], tmp_path)
        use_case.execute(
            tmp_path,
            "NOTE__",
            extra_exclude=("*.tmp",),
            no_default_excludes=True,
        )

        use_case._scanner.index_files.assert_called_once_with(
            tmp_path,
            extra_exclude=("*.tmp",),
            no_default_excludes=True,
        )
