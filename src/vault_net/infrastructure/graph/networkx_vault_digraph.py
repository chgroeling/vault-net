"""NetworkX-backed VaultDiGraph implementation."""

from __future__ import annotations

from typing import cast

import networkx as nx

from vault_net.domain.protocols import VaultDiGraph  # noqa: TC001


class NetworkXVaultDiGraph:
    """Wraps nx.DiGraph, implementing VaultDiGraph protocol."""

    def __init__(self, nx_graph: nx.DiGraph[str]) -> None:
        self._g = nx_graph

    def nodes(self) -> list[str]:
        return list(self._g.nodes())

    def edges(self) -> list[tuple[str, str]]:
        return list(self._g.edges())

    def successors(self, node: str) -> list[str]:
        return list(self._g.successors(node))

    def predecessors(self, node: str) -> list[str]:
        return list(self._g.predecessors(node))

    def bfs_layers(self, source: str) -> list[list[str]]:
        return list(nx.bfs_layers(self._g.to_undirected(), [source]))

    def number_of_nodes(self) -> int:
        return self._g.number_of_nodes()

    def number_of_edges(self) -> int:
        return self._g.number_of_edges()

    def __contains__(self, node: str) -> bool:
        return node in self._g

    def ego_graph(self, source: str, *, radius: int) -> VaultDiGraph:
        ego = nx.ego_graph(self._g, source, radius=radius, undirected=True)
        return NetworkXVaultDiGraph(nx.DiGraph(ego))
