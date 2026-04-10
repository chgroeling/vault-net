"""Vault-wide link resolution implementation."""

from __future__ import annotations

import time
from pathlib import Path

import structlog

from vault_net.consts import _POSSIBLE_EXTENSIONS
from vault_net.models import (
    LinkEdge,
    VaultGraph,
    VaultGraphMetadata,
    VaultIndex,
    VaultLink,
)
from vault_net.utils import _normalize_lookup_key, _path_for_response

logger = structlog.get_logger(__name__)


def _resolve_link_to_file(
    link_path: Path,
    *,
    name_to_file: dict[str, Path],
    stem_to_file: dict[str, Path],
    relative_path_to_file: dict[str, Path],
) -> Path | None:
    """Resolve a file-like link target to a scanned vault file."""
    target_str = str(link_path).strip()

    if not target_str:
        return None

    target_path = Path(target_str)
    target_key = _normalize_lookup_key(target_path)

    path_match = relative_path_to_file.get(target_key)
    if path_match:
        return path_match

    direct_match = name_to_file.get(target_path.name.lower())
    if direct_match:
        return direct_match

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = (
            target_path.with_suffix(ext) if target_path.suffix else Path(f"{target_str}{ext}")
        )
        candidate_path_match = relative_path_to_file.get(_normalize_lookup_key(candidate))
        if candidate_path_match:
            return candidate_path_match

        candidate_match = name_to_file.get(candidate.name.lower())
        if candidate_match:
            return candidate_match

    return stem_to_file.get(target_path.stem.lower())


def _resolve_extracted_link(
    extracted_link: VaultLink,
    resolved_vault: Path,
    *,
    name_to_file: dict[str, Path],
    stem_to_file: dict[str, Path],
    relative_path_to_file: dict[str, Path],
) -> tuple[LinkEdge, Path | None]:
    """Resolve one extracted link into an edge and optional target path."""
    matched = _resolve_link_to_file(
        Path(extracted_link.target),
        name_to_file=name_to_file,
        stem_to_file=stem_to_file,
        relative_path_to_file=relative_path_to_file,
    )
    if matched is None:
        return (
            LinkEdge(
                link=extracted_link,
                resolved=False,
                target_note=None,
                unresolved_reason="not_found",
            ),
            None,
        )

    resolved_target = (resolved_vault / matched).resolve()
    return (
        LinkEdge(
            link=extracted_link,
            resolved=True,
            target_note=_path_for_response(resolved_target, resolved_vault),
        ),
        resolved_target,
    )


def _build_vault_graph(
    vault_root: Path,
    file_paths: list[str],
    file_links: list[list[VaultLink]],
) -> VaultGraph:
    """Resolve all file links for every scanned note in a vault."""
    start = time.monotonic()
    logger.debug("build_vault_graph.start", total_files=len(file_paths))

    # Build lookup maps once
    name_to_file: dict[str, Path] = {}
    stem_to_file: dict[str, Path] = {}
    relative_path_to_file: dict[str, Path] = {}
    for file_path in [Path(fp) for fp in file_paths]:
        name_to_file.setdefault(file_path.name.lower(), file_path)
        stem_to_file.setdefault(file_path.stem.lower(), file_path)
        relative_path_to_file.setdefault(_normalize_lookup_key(file_path), file_path)

    resolved_vault = vault_root.resolve()
    edges: dict[str, list[LinkEdge]] = {}

    for fp, extracted_links in zip(file_paths, file_links, strict=True):
        source_note_path = (resolved_vault / Path(fp)).resolve()
        source_note = _path_for_response(source_note_path, resolved_vault)
        edge_list: list[LinkEdge] = []

        for link in extracted_links:
            edge, _ = _resolve_extracted_link(
                link,
                resolved_vault,
                name_to_file=name_to_file,
                stem_to_file=stem_to_file,
                relative_path_to_file=relative_path_to_file,
            )
            edge_list.append(edge)

        if edge_list:
            edges[source_note] = edge_list

    metadata = VaultGraphMetadata(
        total_files=len(file_paths),
    )
    response = VaultGraph(
        vault_root=str(vault_root),
        metadata=metadata,
        edges=edges,
    )

    duration = time.monotonic() - start
    logger.debug(
        "build_vault_graph.complete",
        duration=round(duration, 4),
        files=response.metadata.total_files,
        edges=len(response.edges),
    )
    return response


def build_vault_graph(vault_index: VaultIndex) -> VaultGraph:
    """Resolve all file links for every scanned note in a vault."""
    files = vault_index.files
    return _build_vault_graph(
        vault_index.vault_root,
        [f.file_path for f in files],
        [f.links for f in files],
    )
