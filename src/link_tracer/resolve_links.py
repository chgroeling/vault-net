"""Single-note link resolution implementation."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path

import structlog

from link_tracer.models import (
    LinkEdge,
    ResolvedFile,
    ResolveMetadata,
    ResolveOptions,
    ResolveResponse,
    ResolveVaultResponse,
)
from link_tracer.utils import _extract_file_links, _normalize_lookup_key, _path_for_response

logger = structlog.get_logger(__name__)

_POSSIBLE_EXTENSIONS = (".md", ".MD", ".markdown")


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


def resolve_links(
    note_path: Path,
    vault_response: ResolveVaultResponse,
    *,
    options: ResolveOptions | None = None,
) -> ResolveResponse:
    """Resolve links in a note against a prebuilt vault edge graph."""
    start = time.monotonic()
    resolved_options = options or ResolveOptions()
    logger.debug("resolve_links.start", note=str(note_path), depth=resolved_options.depth)

    resolved_note = note_path.resolve()
    resolved_vault = Path(vault_response.vault_root).resolve()
    source_note = _path_for_response(resolved_note, resolved_vault)

    files_by_key: dict[str, ResolvedFile] = {}
    for file_entry in vault_response.files:
        files_by_key.setdefault(_normalize_lookup_key(Path(file_entry.file_path)), file_entry)

    name_to_file: dict[str, Path] = {}
    stem_to_file: dict[str, Path] = {}
    relative_path_to_file: dict[str, Path] = {}
    for file_entry in vault_response.files:
        file_path = Path(file_entry.file_path)
        name_to_file.setdefault(file_path.name.lower(), file_path)
        stem_to_file.setdefault(file_path.stem.lower(), file_path)
        relative_path_to_file.setdefault(_normalize_lookup_key(file_path), file_path)

    source_entry = files_by_key.get(_normalize_lookup_key(Path(source_note)))

    if resolved_options.depth == 0:
        if source_entry is None:
            resolved_files = [
                ResolvedFile(
                    file_path=str(resolved_note),
                    frontmatter={},
                    status="ok",
                    error=None,
                    stats=None,
                    file_hash=None,
                ),
            ]
        else:
            resolved_files = [ResolvedFile.from_file_entry(source_entry)]

        metadata = ResolveMetadata.from_files(
            vault_response.metadata.source_directory, resolved_files
        )
        response = ResolveResponse(
            vault_root=vault_response.vault_root,
            source_note=source_note,
            options=resolved_options,
            metadata=metadata,
            files=resolved_files,
            edges={},
        )
    else:
        visited: set[str] = {source_note}
        matched_notes: list[str] = []
        edges: dict[str, list[LinkEdge]] = {}

        queue: deque[tuple[str, int]] = deque()
        queue.append((source_note, 1))

        while queue:
            current_note, current_depth = queue.popleft()

            if current_depth > resolved_options.depth:
                break

            outgoing_links = vault_response.edges.get(current_note)
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

                    if current_depth < resolved_options.depth:
                        queue.append((outgoing.target_note, current_depth + 1))

        matched_paths = {_normalize_lookup_key(Path(path)) for path in matched_notes}
        filtered_files = [
            file_entry
            for file_entry in vault_response.files
            if _normalize_lookup_key(Path(file_entry.file_path)) in matched_paths
        ]

        if source_entry and source_entry not in filtered_files:
            filtered_files = [source_entry, *filtered_files]

        resolved_files = filtered_files

        if source_entry is None:
            resolved_files = [
                ResolvedFile(
                    file_path=str(resolved_note),
                    frontmatter={},
                    status="ok",
                    error=None,
                    stats=None,
                    file_hash=None,
                ),
                *resolved_files,
            ]

        metadata = ResolveMetadata.from_files(
            vault_response.metadata.source_directory, resolved_files
        )

        response = ResolveResponse(
            vault_root=vault_response.vault_root,
            source_note=source_note,
            options=resolved_options,
            metadata=metadata,
            files=resolved_files,
            edges=edges,
        )

    duration = time.monotonic() - start
    logger.debug(
        "resolve_links.complete",
        duration=round(duration, 4),
        files=len(response.files),
        edges=len(response.edges),
    )
    return response
