"""Use case for extracting a note neighborhood graph."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from vault_net.domain.models import VaultGraph
    from vault_net.domain.protocols import GraphBuilder

logger = structlog.get_logger(__name__)


class BuildNeighborhoodGraphUseCase:
    """Build a neighborhood graph around a source note slug."""

    def __init__(self, graph_builder: GraphBuilder) -> None:
        self._graph_builder = graph_builder

    def execute(
        self,
        source_slug: str,
        graph: VaultGraph,
        *,
        depth: int = 1,
    ) -> VaultGraph:
        """Return a neighborhood graph rooted at the provided source slug."""
        start = time.monotonic()
        logger.debug(
            "use_case.build_neighborhood_graph.start",
            source_slug=source_slug,
            depth=depth,
        )

        neighborhood = self._graph_builder.build_neighborhood_graph(source_slug, graph, depth=depth)

        duration = time.monotonic() - start
        logger.info(
            "use_case.build_neighborhood_graph.complete",
            duration=round(duration, 4),
            nodes=neighborhood.digraph.number_of_nodes(),
            edges=neighborhood.metadata.edge_count,
        )
        return neighborhood
