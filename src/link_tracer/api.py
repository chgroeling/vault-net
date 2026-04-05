"""Public API boundary for link tracing."""

from __future__ import annotations

from pathlib import Path

from matterify import scan_directory
from obsilink import extract_links

from link_tracer.models import (
    FileStats,
    TracedFile,
    TraceMetadata,
    TraceOptions,
    TraceResponse,
)

_POSSIBLE_EXTENSIONS = (".md", ".MD", ".markdown")


def _build_vault_lookups(vault_files: list[Path]) -> tuple[dict[str, Path], dict[str, Path]]:
    """Build case-insensitive filename and stem lookup maps.

    Args:
        vault_files: List of file paths from matterify scan.

    Returns:
        Tuple of `(name_to_file, stem_to_file)` maps.
    """
    name_to_file: dict[str, Path] = {}
    stem_to_file: dict[str, Path] = {}

    for file_path in vault_files:
        name_key = file_path.name.lower()
        stem_key = file_path.stem.lower()

        name_to_file.setdefault(name_key, file_path)
        stem_to_file[stem_key] = file_path

    return name_to_file, stem_to_file


def _resolve_link_to_file(
    link_path: Path,
    name_to_file: dict[str, Path],
    stem_to_file: dict[str, Path],
) -> Path | None:
    """Resolve a file-like link target to a scanned vault file.

    Args:
        link_path: Link target as Path from obsilink (target only, no heading/block)
        name_to_file: Case-insensitive filename lookup map.
        stem_to_file: Case-insensitive stem lookup map.

    Returns:
        Matching file path or None
    """
    target_str = str(link_path).strip()

    if not target_str:
        return None

    target_path = Path(target_str)

    direct_match = name_to_file.get(target_path.name.lower())
    if direct_match:
        return direct_match

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = (
            target_path.with_suffix(ext) if target_path.suffix else Path(f"{target_str}{ext}")
        )
        candidate_match = name_to_file.get(candidate.name.lower())
        if candidate_match:
            return candidate_match

    return stem_to_file.get(target_str.lower())


def trace_links(
    note_path: Path,
    vault_root: Path,
    *,
    options: TraceOptions | None = None,
) -> TraceResponse:
    """Scan vault directory and return structured trace response."""
    resolved_options = options or TraceOptions()
    result = scan_directory(vault_root)
    vault_files = [Path(f.file_path) for f in result.files]
    name_to_file, stem_to_file = _build_vault_lookups(vault_files)

    content = note_path.read_text(encoding="utf-8")
    links = extract_links(content)
    file_links = [link for link in links if link.is_file]

    matched_files = []
    for link in file_links:
        matched = _resolve_link_to_file(link.as_path, name_to_file, stem_to_file)
        if matched:
            matched_files.append(matched)

    matched_paths = {str(path) for path in matched_files}
    filtered_files = [f for f in result.files if str(f.file_path) in matched_paths]

    source_entry = next(
        (f for f in result.files if (vault_root / Path(f.file_path)) == note_path),
        None,
    )
    if source_entry and source_entry not in filtered_files:
        filtered_files = [source_entry, *filtered_files]

    total = len(filtered_files)
    with_fm = sum(1 for f in filtered_files if f.frontmatter)
    without_fm = total - with_fm
    errors = sum(1 for f in filtered_files if f.status != "ok")

    traced_files = [
        TracedFile(
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

    return TraceResponse(
        note_path=str(note_path),
        vault_root=str(vault_root),
        options=resolved_options,
        metadata=TraceMetadata(
            source_directory=str(result.metadata.source_directory),
            total_files=total,
            files_with_frontmatter=with_fm,
            files_without_frontmatter=without_fm,
            errors=errors,
        ),
        files=traced_files,
        matched_links=[str(p) for p in matched_files],
    )
