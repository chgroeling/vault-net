"""Use case for building the resolved vault graph."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from vault_net.domain.models import VaultGraph, VaultIndex
    from vault_net.domain.protocols import GraphBuilder

logger = structlog.get_logger(__name__)


class BuildFullGraphUseCase:
    """Build the full vault graph through the graph builder port."""

    def __init__(self, graph_builder: GraphBuilder) -> None:
        self._graph_builder = graph_builder

    def execute(self, vault_index: VaultIndex) -> VaultGraph:
        """Return a resolved graph for the full vault."""
        start = time.monotonic()
        logger.debug("use_case.build_full_graph.start", file_count=len(vault_index.files))

        graph = self._graph_builder.build_full_graph(vault_index)

        duration = time.monotonic() - start
        logger.info(
            "use_case.build_full_graph.complete",
            duration=round(duration, 4),
            edge_count=graph.metadata.edge_count,
        )
        return graph
