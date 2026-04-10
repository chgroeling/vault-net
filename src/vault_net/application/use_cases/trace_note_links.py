"""Use case for tracing links from a single note."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from vault_net.domain.models import NoteLinkTrace

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.protocols import GraphBuilder, VaultScanner

logger = structlog.get_logger(__name__)


class TraceNoteLinksUseCase:
    """Orchestrate vault scan, full graph build, and neighborhood extraction."""

    def __init__(self, scanner: VaultScanner, graph_builder: GraphBuilder) -> None:
        self._scanner = scanner
        self._graph_builder = graph_builder

    def execute(
        self,
        vault_root: Path,
        source_slug: str,
        *,
        depth: int = 1,
        extra_exclude_dir: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> NoteLinkTrace:
        """Scan vault, build graph, and extract neighborhood around source slug."""
        start = time.monotonic()
        logger.info(
            "use_case.trace_note_links.start",
            source_slug=source_slug,
            vault_root=str(vault_root),
            depth=depth,
        )

        logger.debug("use_case.trace_note_links.step.scanning")
        vault_index = self._scanner.scan(
            vault_root,
            extra_exclude_dir=extra_exclude_dir,
            no_default_excludes=no_default_excludes,
        )

        logger.debug("use_case.trace_note_links.step.building_full_graph")
        full_graph = self._graph_builder.build_full_graph(vault_index)

        logger.debug("use_case.trace_note_links.step.extracting_neighborhood")
        neighborhood_graph = self._graph_builder.build_neighborhood_graph(
            source_slug, full_graph, depth=depth
        )

        duration = time.monotonic() - start
        logger.info(
            "use_case.trace_note_links.complete",
            duration=round(duration, 4),
            total_files=vault_index.metadata.total_files,
            neighborhood_nodes=neighborhood_graph.digraph.number_of_nodes(),
        )

        return NoteLinkTrace(
            source_slug=source_slug,
            vault_index=vault_index,
            neighborhood_graph=neighborhood_graph,
        )
