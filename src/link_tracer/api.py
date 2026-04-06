"""Public API boundary for link resolution."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from matterify import scan_directory
from obsilink import extract_links

from link_tracer.models import (
    ResolvedFile,
    ResolveMetadata,
    ResolveOptions,
    ResolveResponse,
    VaultIndex,
    _normalize_lookup_key,
)

if TYPE_CHECKING:
    from matterify.models import AggregatedResult, FileEntry

_POSSIBLE_EXTENSIONS = (".md", ".MD", ".markdown")


def _resolve_link_to_file(
    link_path: Path,
    vault_index: VaultIndex,
) -> Path | None:
    """Resolve a file-like link target to a scanned vault file.

    Args:
        link_path: Link target as Path from obsilink (target only, no heading/block)
        vault_index: Prebuilt vault index with lookup maps.

    Returns:
        Matching file path or None
    """
    target_str = str(link_path).strip()

    if not target_str:
        return None

    target_path = Path(target_str)
    target_key = _normalize_lookup_key(target_path)

    path_match = vault_index.relative_path_to_file.get(target_key)
    if path_match:
        return path_match

    direct_match = vault_index.name_to_file.get(target_path.name.lower())
    if direct_match:
        return direct_match

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = (
            target_path.with_suffix(ext) if target_path.suffix else Path(f"{target_str}{ext}")
        )
        candidate_path_match = vault_index.relative_path_to_file.get(
            _normalize_lookup_key(candidate)
        )
        if candidate_path_match:
            return candidate_path_match

        candidate_match = vault_index.name_to_file.get(candidate.name.lower())
        if candidate_match:
            return candidate_match

    return vault_index.stem_to_file.get(target_path.stem.lower())


def build_vault_index(  # type: ignore[no-any-unimported]
    vault_root: Path,
    scan_result: AggregatedResult,
) -> VaultIndex:
    """Build a VaultIndex from an existing scan result.

    Args:
        vault_root: Root directory of the vault.
        scan_result: AggregatedResult from matterify.scan_directory().

    Returns:
        VaultIndex with prebuilt lookup maps.
    """
    return VaultIndex.from_scan_result(vault_root, scan_result)


def scan_vault(vault_root: Path) -> VaultIndex:
    """Scan vault directory and build a VaultIndex.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        VaultIndex with scan results and prebuilt lookup maps.
    """
    scan_result = scan_directory(vault_root)
    return build_vault_index(vault_root, scan_result)


def _traverse_links(
    note_path: Path,
    vault_index: VaultIndex,
    resolved_vault: Path,
    resolved_note: Path,
    options: ResolveOptions,
) -> list[Path]:
    """BFS traversal of note links up to the specified depth.

    Args:
        note_path: Path to the starting note file.
        vault_index: Prebuilt VaultIndex with lookup maps.
        resolved_vault: Resolved absolute path of the vault root.
        resolved_note: Resolved absolute path of the source note.
        options: Resolve options including depth.

    Returns:
        List of matched file paths (relative) discovered during traversal.
    """
    visited: set[Path] = set()
    matched_files: list[Path] = []

    queue: deque[tuple[Path, int]] = deque()
    queue.append((note_path, 1))
    visited.add(resolved_note)

    while queue:
        current_note_path, current_depth = queue.popleft()

        if current_depth > options.depth:
            break

        content = current_note_path.read_text(encoding="utf-8")
        links = extract_links(content)
        file_links = [link for link in links if link.is_file]

        for link in file_links:
            matched = _resolve_link_to_file(link.as_path, vault_index)
            if matched is None:
                continue
            resolved_child = (resolved_vault / matched).resolve()
            if resolved_child not in visited:
                matched_files.append(matched)
                visited.add(resolved_child)

                if current_depth < options.depth:
                    queue.append((resolved_child, current_depth + 1))

    return matched_files


def resolve_links(
    note_path: Path,
    vault_index: VaultIndex,
    *,
    options: ResolveOptions | None = None,
) -> ResolveResponse:
    """Resolve links in a note against a prebuilt vault index.

    Args:
        note_path: Path to the note file to trace.
        vault_index: Prebuilt VaultIndex from scan_vault() or build_vault_index().
        options: Optional resolve options.

    Returns:
        ResolveResponse with matched files and metadata.
    """
    resolved_options = options or ResolveOptions()

    resolved_note = note_path.resolve()
    resolved_vault = vault_index.vault_root.resolve()

    source_entry: FileEntry | None = None  # type: ignore[no-any-unimported]
    try:
        source_note = str(resolved_note.relative_to(resolved_vault))
        source_entry = next(
            (
                f
                for f in vault_index.files
                if (resolved_vault / Path(f.file_path)).resolve() == resolved_note
            ),
            None,
        )
    except ValueError:
        source_note = str(resolved_note)

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

        metadata = ResolveMetadata.from_files(vault_index.source_directory, resolved_files)

        return ResolveResponse(
            vault_root=str(vault_index.vault_root),
            source_note=source_note,
            options=resolved_options,
            metadata=metadata,
            files=resolved_files,
            matched_links=[],
        )

    matched_files = _traverse_links(
        note_path, vault_index, resolved_vault, resolved_note, resolved_options
    )

    matched_paths = {str(path) for path in matched_files}
    filtered_files = [f for f in vault_index.files if str(f.file_path) in matched_paths]

    if source_entry and source_entry not in filtered_files:
        filtered_files = [source_entry, *filtered_files]

    resolved_files = [ResolvedFile.from_file_entry(f) for f in filtered_files]

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

    metadata = ResolveMetadata.from_files(vault_index.source_directory, resolved_files)

    return ResolveResponse(
        vault_root=str(vault_index.vault_root),
        source_note=source_note,
        options=resolved_options,
        metadata=metadata,
        files=resolved_files,
        matched_links=[str(p) for p in matched_files],
    )
