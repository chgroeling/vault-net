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


def _resolve_link_to_file(link_target: str, vault_files: list[Path]) -> Path | None:
    """Resolve a file-like link target to a scanned vault file.

    Args:
        link_target: Link target from obsilink (target only, no heading/block)
        vault_files: List of file paths from matterify scan

    Returns:
        Matching file path or None
    """
    target_str = link_target.strip()
    target_path = Path(target_str)

    if not target_str:
        return None

    stem_to_file: dict[str, Path] = {}
    for f in vault_files:
        stem_to_file[f.stem.lower()] = f

    for f in vault_files:
        if f.name.lower() == target_path.name.lower():
            return f

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = target_path.with_suffix(ext) if target_path.suffix else Path(target_str + ext)
        for f in vault_files:
            if f.name.lower() == candidate.name.lower():
                return f

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

    content = note_path.read_text(encoding="utf-8")
    links = extract_links(content)
    file_links = [link for link in links if link.is_file]

    matched_files = []
    for link in file_links:
        matched = _resolve_link_to_file(link.target, vault_files)
        if matched:
            matched_files.append(matched)

    matched_set = {str(p) for p in matched_files}
    filtered_files = [f for f in result.files if str(f.file_path) in matched_set]

    source_entry = next(
        (f for f in result.files if str(vault_root / f.file_path) == str(note_path)),
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
