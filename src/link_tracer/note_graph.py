"""Single-note link resolution implementation."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path

import structlog

from link_tracer.consts import _POSSIBLE_EXTENSIONS
from link_tracer.models import (
    LinkEdge,
    VaultGraph,
    VaultGraphMetadata,
    VaultIndex,
)
from link_tracer.utils import _extract_file_links, _normalize_lookup_key, _path_for_response

logger = structlog.get_logger(__name__)


def _resolve_link_target_with_lookups(
    target: str,
    *,
    name_to_file: dict[str, Path],
    stem_to_file: dict[str, Path],
    relative_path_to_file: dict[str, Path],
) -> Path | None:
    """Resolve one extracted link target using prebuilt lookup maps."""
    target_str = target.strip()
    if not target_str:
        return None

    target_path = Path(target_str)
    target_key = _normalize_lookup_key(target_path)

    path_match = relative_path_to_file.get(target_key)
    if path_match is not None:
        return path_match

    direct_match = name_to_file.get(target_path.name.lower())
    if direct_match is not None:
        return direct_match

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = (
            target_path.with_suffix(ext) if target_path.suffix else Path(f"{target_str}{ext}")
        )
        candidate_path_match = relative_path_to_file.get(_normalize_lookup_key(candidate))
        if candidate_path_match is not None:
            return candidate_path_match

        candidate_match = name_to_file.get(candidate.name.lower())
        if candidate_match is not None:
            return candidate_match

    return stem_to_file.get(target_path.stem.lower())


def _build_reverse_index(
    edges: dict[str, list[LinkEdge]],
) -> dict[str, list[tuple[str, LinkEdge]]]:
    """Build a reverse lookup from target_note to (source_note, edge) pairs."""
    reverse: dict[str, list[tuple[str, LinkEdge]]] = {}
    for source_note, outgoing in edges.items():
        for edge in outgoing:
            if edge.resolved and edge.target_note is not None:
                reverse.setdefault(edge.target_note, []).append((source_note, edge))
    return reverse


def build_note_graph(
    note_path: Path,
    vault_graph: VaultGraph,
    vault_index: VaultIndex,
    *,
    depth: int = 1,
) -> tuple[str, VaultGraph]:
    """Resolve links in a note and return the source note path and scoped link graph."""
    if depth < 0:
        raise ValueError(f"depth must be >= 0, got {depth}")
    start = time.monotonic()
    logger.debug("build_note_graph.start", note=str(note_path), depth=depth)

    resolved_note = note_path.resolve()
    resolved_vault = Path(vault_graph.vault_root).resolve()
    source_note = _path_for_response(resolved_note, resolved_vault)

    # Build lookup maps locally
    name_to_file: dict[str, Path] = {}
    stem_to_file: dict[str, Path] = {}
    relative_path_to_file: dict[str, Path] = {}
    for file_path in [Path(f.file_path) for f in vault_index.files]:
        name_to_file.setdefault(file_path.name.lower(), file_path)
        stem_to_file.setdefault(file_path.stem.lower(), file_path)
        relative_path_to_file.setdefault(_normalize_lookup_key(file_path), file_path)

    files_by_key = {_normalize_lookup_key(Path(str(fe.file_path))): fe for fe in vault_index.files}

    source_entry = files_by_key.get(_normalize_lookup_key(Path(source_note)))

    if depth == 0:
        if source_entry is None:
            metadata = VaultGraphMetadata(
                source_directory=vault_graph.metadata.source_directory,
                total_files=1,
                errors=0,
            )
        else:
            metadata = VaultGraphMetadata(
                source_directory=vault_graph.metadata.source_directory,
                total_files=1,
                errors=0 if source_entry.status == "ok" else 1,
            )
        graph = VaultGraph(
            vault_root=vault_graph.vault_root,
            metadata=metadata,
            edges={},
        )
    else:
        reverse_index = _build_reverse_index(vault_graph.edges)
        visited: set[str] = {source_note}
        matched_notes: list[str] = []
        edges: dict[str, list[LinkEdge]] = {}

        queue: deque[tuple[str, int]] = deque()
        queue.append((source_note, 1))

        while queue:
            current_note, current_depth = queue.popleft()

            if current_depth > depth:
                break

            # --- Forward edges ---
            outgoing_links = vault_graph.edges.get(current_note)
            if outgoing_links is None:
                current_note_path = Path(current_note)
                if not current_note_path.is_absolute():
                    current_note_path = (resolved_vault / current_note_path).resolve()

                content = current_note_path.read_text(encoding="utf-8")
                extracted_links = _extract_file_links(content)
                outgoing_links = []
                for extracted_link in extracted_links:
                    matched = _resolve_link_target_with_lookups(
                        extracted_link.target,
                        name_to_file=name_to_file,
                        stem_to_file=stem_to_file,
                        relative_path_to_file=relative_path_to_file,
                    )
                    if matched is None:
                        outgoing_links.append(
                            LinkEdge(
                                link=extracted_link,
                                resolved=False,
                                target_note=None,
                                unresolved_reason="not_found",
                            )
                        )
                        continue

                    outgoing_links.append(
                        LinkEdge(
                            link=extracted_link,
                            resolved=True,
                            target_note=str(matched),
                        )
                    )

            if outgoing_links:
                edges[current_note] = outgoing_links

            for outgoing in outgoing_links:
                if not outgoing.resolved or outgoing.target_note is None:
                    continue

                if outgoing.target_note not in visited:
                    matched_notes.append(outgoing.target_note)
                    visited.add(outgoing.target_note)

                    if current_depth < depth:
                        queue.append((outgoing.target_note, current_depth + 1))

            # --- Backlink edges ---
            for backlink_source, original_edge in reverse_index.get(current_note, []):
                if backlink_source not in edges:
                    edges.setdefault(backlink_source, []).append(original_edge)

                if backlink_source not in visited:
                    matched_notes.append(backlink_source)
                    visited.add(backlink_source)

                    if current_depth < depth:
                        queue.append((backlink_source, current_depth + 1))

        matched_paths = {_normalize_lookup_key(Path(path)) for path in matched_notes}
        filtered_files = [files_by_key[key] for key in matched_paths if key in files_by_key]

        if source_entry and source_entry not in filtered_files:
            filtered_files = [source_entry, *filtered_files]

    extra = 0 if source_entry else 1
    total = len(filtered_files) + extra
    errors = sum(1 for f in filtered_files if f.status != "ok")
    metadata = VaultGraphMetadata(
        source_directory=vault_graph.metadata.source_directory,
        total_files=total,
        errors=errors,
    )

    graph = VaultGraph(
        vault_root=vault_graph.vault_root,
        metadata=metadata,
        edges=edges,
    )

    duration = time.monotonic() - start
    logger.debug(
        "build_note_graph.complete",
        duration=round(duration, 4),
        files=graph.metadata.total_files,
        edges=len(graph.edges),
    )
    return source_note, graph
