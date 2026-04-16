"""Domain ports used by application use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.models import VaultGraph, VaultIndex, VaultLink, VaultListing


class VaultDiGraph(Protocol):
    """Minimal graph interface needed by domain and interface layers."""

    def nodes(self) -> Iterable[str]: ...

    def edges(self) -> Iterable[tuple[str, str]]: ...

    def successors(self, node: str) -> Iterable[str]: ...

    def predecessors(self, node: str) -> Iterable[str]: ...

    def bfs_layers(self, source: str) -> list[list[str]]: ...

    def number_of_nodes(self) -> int: ...

    def number_of_edges(self) -> int: ...

    def __contains__(self, node: str) -> bool: ...

    def ego_graph(self, source: str, *, radius: int) -> VaultDiGraph: ...


class VaultScanner(Protocol):
    """Port for scanning vault content into a domain index."""

    def scan(
        self,
        vault_root: Path,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> tuple[VaultIndex, dict[str, list[VaultLink]]]:
        """Scan the vault and return a domain index with note links."""

    def index_files(
        self,
        vault_root: Path,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> VaultListing:
        """Index vault files into a lightweight listing of slugs and paths."""


class GraphBuilder(Protocol):
    """Port for graph construction and traversal."""

    def build_full_graph(
        self,
        vault_index: VaultIndex,
        note_links: dict[str, list[VaultLink]],
    ) -> VaultGraph:
        """Build a resolved graph from a vault index."""

    def build_neighborhood_graph(
        self,
        source_slug: str,
        graph: VaultGraph,
        *,
        depth: int = 1,
    ) -> VaultGraph:
        """Build a neighborhood graph around a source slug."""
