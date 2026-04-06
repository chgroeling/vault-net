"""Public API boundary for link resolution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from matterify import scan_directory
from obsilink import extract_links

from link_tracer.models import (
    FileStats,
    ResolvedFile,
    ResolveMetadata,
    ResolveOptions,
    ResolveResponse,
    VaultIndex,
)

if TYPE_CHECKING:
    from matterify.models import AggregatedResult

_POSSIBLE_EXTENSIONS = (".md", ".MD", ".markdown")


def _normalize_lookup_key(path: Path) -> str:
    """Return a case-insensitive normalized lookup key for paths."""
    return path.as_posix().lstrip("./").lower()


def _build_vault_lookups(
    vault_files: list[Path],
) -> tuple[dict[str, Path], dict[str, Path], dict[str, Path]]:
    """Build case-insensitive lookup maps for vault files.

    Args:
        vault_files: List of file paths from matterify scan.

    Returns:
        Tuple of `(name_to_file, stem_to_file, relative_path_to_file)` maps.
    """
    name_to_file: dict[str, Path] = {}
    stem_to_file: dict[str, Path] = {}
    relative_path_to_file: dict[str, Path] = {}

    for file_path in vault_files:
        name_key = file_path.name.lower()
        stem_key = file_path.stem.lower()
        relative_key = _normalize_lookup_key(file_path)

        name_to_file.setdefault(name_key, file_path)
        stem_to_file.setdefault(stem_key, file_path)
        relative_path_to_file.setdefault(relative_key, file_path)

    return name_to_file, stem_to_file, relative_path_to_file


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


def build_vault_context(  # type: ignore[no-any-unimported]
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
    vault_files = [Path(f.file_path) for f in scan_result.files]
    name_to_file, stem_to_file, relative_path_to_file = _build_vault_lookups(vault_files)

    return VaultIndex(
        vault_root=vault_root,
        files=scan_result.files,
        source_directory=str(scan_result.metadata.source_directory),
        name_to_file=name_to_file,
        stem_to_file=stem_to_file,
        relative_path_to_file=relative_path_to_file,
    )


def scan_vault(vault_root: Path) -> VaultIndex:
    """Scan vault directory and build a VaultIndex.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        VaultIndex with scan results and prebuilt lookup maps.
    """
    scan_result = scan_directory(vault_root)
    return build_vault_context(vault_root, scan_result)


def resolve_links(
    note_path: Path,
    vault_index: VaultIndex,
    *,
    options: ResolveOptions | None = None,
) -> ResolveResponse:
    """Resolve links in a note against a prebuilt vault index.

    Args:
        note_path: Path to the note file to trace.
        vault_index: Prebuilt VaultIndex from scan_vault() or build_vault_context().
        options: Optional resolve options.

    Returns:
        ResolveResponse with matched files and metadata.
    """
    resolved_options = options or ResolveOptions()

    content = note_path.read_text(encoding="utf-8")
    links = extract_links(content)
    file_links = [link for link in links if link.is_file]

    matched_files = []
    for link in file_links:
        matched = _resolve_link_to_file(link.as_path, vault_index)
        if matched:
            matched_files.append(matched)

    matched_paths = {str(path) for path in matched_files}
    filtered_files = [f for f in vault_index.files if str(f.file_path) in matched_paths]

    source_entry = next(
        (f for f in vault_index.files if (vault_index.vault_root / Path(f.file_path)) == note_path),
        None,
    )
    if source_entry and source_entry not in filtered_files:
        filtered_files = [source_entry, *filtered_files]

    total = len(filtered_files)
    with_fm = sum(1 for f in filtered_files if f.frontmatter)
    without_fm = total - with_fm
    errors = sum(1 for f in filtered_files if f.status != "ok")

    resolved_files = [
        ResolvedFile(
            file_path=str(f.file_path),
            frontmatter=f.frontmatter,
            status=f.status,
            error=f.error,
            stats=FileStats(
                file_size=f.stats.file_size,
                modified_time=f.stats.modified_time,
                access_time=f.stats.access_time,
            )
            if f.stats
            else None,
            file_hash=f.file_hash,
        )
        for f in filtered_files
    ]

    return ResolveResponse(
        vault_root=str(vault_index.vault_root),
        options=resolved_options,
        metadata=ResolveMetadata(
            source_directory=vault_index.source_directory,
            total_files=total,
            files_with_frontmatter=with_fm,
            files_without_frontmatter=without_fm,
            errors=errors,
        ),
        files=resolved_files,
        matched_links=[str(p) for p in matched_files],
    )
