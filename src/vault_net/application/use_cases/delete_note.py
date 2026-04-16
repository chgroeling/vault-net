"""Use case for deleting a note from the vault."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from vault_net.domain.services.vault_registry import VaultFileLookup

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.protocols import VaultScanner

logger = structlog.get_logger(__name__)


class DeleteNoteUseCase:
    """Delete a note from the vault by slug or path."""

    def __init__(self, scanner: VaultScanner) -> None:
        self._scanner = scanner

    def execute(
        self,
        vault_root: Path,
        note_input: str,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> str:
        """Resolve input to a slug, delete the file, and return its path.

        Args:
            vault_root: Root directory of the vault.
            note_input: Slug or relative file path identifying the note.
            extra_exclude: Additional glob patterns to exclude from scanning.
            no_default_excludes: Disable built-in default exclusions.

        Returns:
            The file path of the deleted note (relative to vault root).

        Raises:
            KeyError: If the slug or path cannot be resolved.
            FileNotFoundError: If the resolved file does not exist on disk.
        """
        logger.info("use_case.delete_note.start", note_input=note_input)

        listing = self._scanner.index_files(
            vault_root,
            extra_exclude=extra_exclude,
            no_default_excludes=no_default_excludes,
        )

        lookup = VaultFileLookup(listing)
        slug = lookup.resolve_to_slug(note_input, vault_root)
        if slug is None:
            raise KeyError(note_input)
        note = lookup.get_file(slug)
        if note is None:
            raise KeyError(note_input)

        target = (vault_root / note.file_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Note file does not exist: {target}")

        target.unlink()
        logger.info("use_case.delete_note.done", slug=slug, path=str(target))
        return note.file_path
