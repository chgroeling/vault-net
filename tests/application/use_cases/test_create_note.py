"""Tests for CreateNoteUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vault_net.application.use_cases.create_note import CreateNoteUseCase
from vault_net.domain.models import VaultFile, VaultListing


def _make_use_case(files: list[VaultFile] | None = None) -> CreateNoteUseCase:
    scanner = MagicMock()
    listing = MagicMock(spec=VaultListing)
    listing.files = files or []
    scanner.index_files.return_value = listing
    return CreateNoteUseCase(scanner=scanner)


class TestCreateNoteUseCase:
    """Verify CreateNoteUseCase behavior."""

    def test_creates_note_with_md_extension(self, tmp_path: Path) -> None:
        """Append .md when the caller omits it."""
        use_case = _make_use_case()
        slug = use_case.execute(tmp_path, "hello")

        assert (tmp_path / "hello.md").exists()
        assert slug

    def test_preserves_explicit_md_extension(self, tmp_path: Path) -> None:
        """Do not double-append .md when already present."""
        use_case = _make_use_case()
        use_case.execute(tmp_path, "hello.md")

        assert (tmp_path / "hello.md").exists()
        assert not (tmp_path / "hello.md.md").exists()

    def test_creates_subdirectories(self, tmp_path: Path) -> None:
        """Create intermediate directories when note path includes them."""
        use_case = _make_use_case()
        slug = use_case.execute(tmp_path, "sub/dir/my-note")

        assert (tmp_path / "sub" / "dir" / "my-note.md").exists()
        assert slug

    def test_writes_content(self, tmp_path: Path) -> None:
        """Write caller-supplied content into the note."""
        use_case = _make_use_case()
        use_case.execute(tmp_path, "note", content="# Hello\n\nWorld")

        text = (tmp_path / "note.md").read_text(encoding="utf-8")
        assert text == "# Hello\n\nWorld"

    def test_empty_content_by_default(self, tmp_path: Path) -> None:
        """An empty string is written when no content is given."""
        use_case = _make_use_case()
        use_case.execute(tmp_path, "note")

        text = (tmp_path / "note.md").read_text(encoding="utf-8")
        assert text == ""

    def test_raises_on_existing_file(self, tmp_path: Path) -> None:
        """Raise FileExistsError when the target already exists."""
        (tmp_path / "dup.md").write_text("existing", encoding="utf-8")
        use_case = _make_use_case()

        with pytest.raises(FileExistsError):
            use_case.execute(tmp_path, "dup")

    def test_force_overwrites_existing_file(self, tmp_path: Path) -> None:
        """--force overwrites an existing note without error."""
        (tmp_path / "dup.md").write_text("old", encoding="utf-8")
        use_case = _make_use_case()
        use_case.execute(tmp_path, "dup", content="new", force=True)

        assert (tmp_path / "dup.md").read_text(encoding="utf-8") == "new"

    def test_raises_on_path_traversal(self, tmp_path: Path) -> None:
        """Reject paths that escape the vault root."""
        use_case = _make_use_case()

        with pytest.raises(ValueError, match="escapes vault root"):
            use_case.execute(tmp_path, "../../etc/passwd")

    def test_returns_slug_from_stem(self, tmp_path: Path) -> None:
        """Return a slug derived from the file stem."""
        use_case = _make_use_case()
        slug = use_case.execute(tmp_path, "my-note")

        assert slug == "MY_NOTE_"

    def test_slug_avoids_collision_with_existing_notes(self, tmp_path: Path) -> None:
        """Generate a unique slug when the base slug is already taken."""
        existing = VaultFile(slug="MY_NOTE_", file_path="my-note.md")
        use_case = _make_use_case([existing])

        slug = use_case.execute(tmp_path, "my-note")

        assert slug != "MY_NOTE_"
        assert slug.startswith("MY_NOTE")
