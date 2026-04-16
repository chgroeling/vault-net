"""Use case for showing detailed information about a single note."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from vault_net.domain.models import NoteShow, VaultFile
from vault_net.domain.services.vault_registry import VaultRegistry

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.protocols import GraphBuilder, VaultScanner

logger = structlog.get_logger(__name__)


class ShowNoteUseCase:
    """Orchestrate vault scan, full graph build, and note details extraction."""

    def __init__(self, scanner: VaultScanner, graph_builder: GraphBuilder) -> None:
        self._scanner = scanner
        self._graph_builder = graph_builder

    def execute(
        self,
        vault_root: Path,
        note_input: str,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
        include_content: bool = True,
    ) -> NoteShow:
        """Scan vault, build graph, and show note details with links."""
        start = time.monotonic()
        logger.info(
            "use_case.show_note.start",
            note_input=note_input,
            vault_root=str(vault_root),
        )

        logger.debug("use_case.show_note.step.scanning")
        vault_index, note_links = self._scanner.scan(
            vault_root,
            extra_exclude=extra_exclude,
            no_default_excludes=no_default_excludes,
        )

        registry = VaultRegistry(vault_index)
        source_slug = registry.resolve_to_slug(note_input, vault_root)
        if source_slug is None:
            raise KeyError(note_input)

        logger.debug("use_case.show_note.step.building_full_graph")
        full_graph = self._graph_builder.build_full_graph(vault_index, note_links)

        logger.debug(
            "use_case.show_note.step.resolving_links",
            resolved_slug=source_slug,
        )
        source_note = registry.get_note(source_slug)
        if source_note is None:
            raise KeyError(source_slug)

        forward_slugs = list(full_graph.digraph.successors(source_slug))
        backward_slugs = list(full_graph.digraph.predecessors(source_slug))

        forward_links: list[VaultFile] = []
        for slug in forward_slugs:
            file = registry.get_file(slug)
            if file is not None:
                forward_links.append(VaultFile(slug=file.slug, file_path=file.file_path))

        backward_links: list[VaultFile] = []
        for slug in backward_slugs:
            file = registry.get_file(slug)
            if file is not None:
                backward_links.append(VaultFile(slug=file.slug, file_path=file.file_path))

        duration = time.monotonic() - start
        logger.info(
            "use_case.show_note.complete",
            duration=round(duration, 4),
            total_files=vault_index.metadata.total_files,
            forward_link_count=len(forward_links),
            backward_link_count=len(backward_links),
        )

        content = _read_file_content(vault_root, source_note.file_path) if include_content else None

        return NoteShow(
            note=source_note,
            forward_links=forward_links,
            backward_links=backward_links,
            content=content,
        )


def _read_file_content(vault_root: Path, file_path: str) -> str | None:
    """Read the text content of a vault file, return None on failure."""
    full_path = vault_root / file_path
    try:
        return full_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("show_note.read_content_failed", path=str(full_path))
        return None
