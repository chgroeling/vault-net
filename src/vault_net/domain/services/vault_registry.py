"""Lookup services for converting between slugs and files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vault_net.domain.models import VaultFile, VaultIndex, VaultNote


class VaultRegistry:
    """Provide bidirectional lookup between slugs and `VaultNote` entries."""

    def __init__(self, vault_index: VaultIndex) -> None:
        self._slug_to_file: dict[str, VaultNote] = {file.slug: file for file in vault_index.files}
        self._file_path_to_slug: dict[str, str] = {
            file.file_path: file.slug for file in vault_index.files
        }

    def get_file(self, slug: str) -> VaultNote | None:
        """Return the note for a slug, if present."""
        return self._slug_to_file.get(slug)

    def get_slug(self, file: VaultFile) -> str | None:
        """Return the slug for a file identity, if present."""
        return self._file_path_to_slug.get(file.file_path)

    def get_slug_by_path(self, file_path: str) -> str | None:
        """Return the slug for a file path string, if present."""
        return self._file_path_to_slug.get(file_path)

    def resolve_to_slug(self, note_input: str, vault_root: Path) -> str | None:
        """Resolve a note input to its corresponding slug.

        Resolution order:
        1. Direct slug lookup in the registry
        2. Relative path lookup (as stored in registry)
        3. Absolute path -> relative to vault root -> lookup

        Args:
            note_input: A slug, relative path, or absolute path identifying a note.
            vault_root: The root directory of the vault (used for resolving relative
                paths and converting absolute paths to vault-relative paths).

        Returns:
            The slug string if the note was found, or None if resolution failed.
        """
        note_by_slug = self.get_file(note_input)
        if note_by_slug is not None:
            return note_by_slug.slug

        slug_by_path = self.get_slug_by_path(note_input)
        if slug_by_path is not None:
            return slug_by_path

        input_path = Path(note_input)
        if not input_path.is_absolute():
            input_path = (vault_root / input_path).resolve()
        else:
            input_path = input_path.resolve()

        if not input_path.exists():
            return None

        try:
            relative_path = input_path.relative_to(vault_root)
            return self.get_slug_by_path(str(relative_path))
        except ValueError:
            return None
