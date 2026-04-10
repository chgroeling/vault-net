"""Build resolved digraph representations from a vault index."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import networkx as nx
import structlog

from vault_net.consts import _POSSIBLE_EXTENSIONS
from vault_net.models import VaultGraph, VaultGraphMetadata
from vault_net.utils import _normalize_lookup_key

if TYPE_CHECKING:
    from vault_net.models import VaultIndex, VaultNote

logger = structlog.get_logger(__name__)


def _resolve_link_to_slug(
    link_path: Path,
    *,
    name_to_slug: dict[str, str],
    stem_to_slug: dict[str, str],
    relative_path_to_slug: dict[str, str],
) -> str | None:
    """Resolve a file-like link target to a scanned vault file slug."""
    target_str = str(link_path).strip()
    if not target_str:
        return None

    target_path = Path(target_str)
    target_key = _normalize_lookup_key(target_path)

    path_match = relative_path_to_slug.get(target_key)
    if path_match is not None:
        return path_match

    direct_match = name_to_slug.get(target_path.name.lower())
    if direct_match is not None:
        return direct_match

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = (
            target_path.with_suffix(ext) if target_path.suffix else Path(f"{target_str}{ext}")
        )
        candidate_path_match = relative_path_to_slug.get(_normalize_lookup_key(candidate))
        if candidate_path_match is not None:
            return candidate_path_match

        candidate_name_match = name_to_slug.get(candidate.name.lower())
        if candidate_name_match is not None:
            return candidate_name_match

    return stem_to_slug.get(target_path.stem.lower())


def _build_lookup_maps(
    files: list[VaultNote],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Build path/name/stem lookup maps from scanned files to slugs."""
    name_to_slug: dict[str, str] = {}
    stem_to_slug: dict[str, str] = {}
    relative_path_to_slug: dict[str, str] = {}

    for file in files:
        file_path = Path(file.file_path)
        name_to_slug.setdefault(file_path.name.lower(), file.slug)
        stem_to_slug.setdefault(file_path.stem.lower(), file.slug)
        relative_path_to_slug.setdefault(_normalize_lookup_key(file_path), file.slug)

    return name_to_slug, stem_to_slug, relative_path_to_slug


def _build_vault_slug_edge_list(vault_index: VaultIndex) -> list[tuple[str, str]]:
    """Return a deduplicated resolved edge list as slug pairs.

    The result format is compatible with `networkx.from_edgelist`.

    """
    files = vault_index.files
    name_to_slug, stem_to_slug, relative_path_to_slug = _build_lookup_maps(files)

    edges: set[tuple[str, str]] = set()

    for file in files:
        source_slug = file.slug
        for link in file.links:
            target_slug = _resolve_link_to_slug(
                Path(link.target),
                name_to_slug=name_to_slug,
                stem_to_slug=stem_to_slug,
                relative_path_to_slug=relative_path_to_slug,
            )
            if target_slug is None:
                continue
            if target_slug == source_slug:
                logger.warning(
                    "_build_vault_slug_edge_list.self_loop_skipped",
                    source_slug=source_slug,
                    target_slug=target_slug,
                )
                continue
            edges.add((source_slug, target_slug))

    return sorted(edges)


def build_vault_digraph(vault_index: VaultIndex) -> VaultGraph:
    """Build a resolved vault graph whose nodes are note slugs."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    slug_edges = _build_vault_slug_edge_list(vault_index)
    graph.add_edges_from(slug_edges)
    graph.add_nodes_from(file.slug for file in vault_index.files)

    return VaultGraph(
        vault_root=vault_index.vault_root,
        metadata=VaultGraphMetadata(edge_count=len(slug_edges)),
        digraph=graph,
    )


def build_note_ego_graph(
    source_slug: str,
    vault_digraph: nx.DiGraph[str],
    *,
    depth: int = 1,
) -> nx.DiGraph[str]:
    """Return the directed ego graph around `source_slug`."""
    if depth < 0:
        raise ValueError(f"depth must be >= 0, got {depth}")
    if source_slug not in vault_digraph:
        raise KeyError(source_slug)

    ego = nx.ego_graph(vault_digraph, source_slug, radius=depth, undirected=True)
    return nx.DiGraph(ego)


__all__ = [
    "build_note_ego_graph",
    "build_vault_digraph",
]
