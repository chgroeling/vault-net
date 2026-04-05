"""Public API boundary for link tracing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from matterify import scan_directory
from obsilink import extract_links

from link_tracer.models import TraceOptions

_POSSIBLE_EXTENSIONS = (".md", ".MD", ".markdown")


def _resolve_link_to_file(link_target: str, vault_files: list[Path]) -> Path | None:
    """Resolve a link target to a file path from matterify scan results.

    Args:
        link_target: The raw link target from obsilink (may or may not have extension)
        vault_files: List of file paths from matterify scan

    Returns:
        Matching file path or None
    """
    target = link_target.split("#")[0].split("^")[0].strip()

    if not target:
        return None

    stem_to_file: dict[str, Path] = {}
    for f in vault_files:
        stem_to_file[f.stem.lower()] = f

    target_path = Path(target)

    for f in vault_files:
        if f.name.lower() == target_path.name.lower():
            return f

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = target_path.with_suffix(ext) if target_path.suffix else Path(target + ext)
        for f in vault_files:
            if f.name.lower() == candidate.name.lower():
                return f

    return stem_to_file.get(target.lower())


def trace_links(
    note_path: Path,
    vault_root: Path,
    *,
    options: TraceOptions | None = None,
) -> dict[str, Any]:
    """Scan vault directory and return structured trace response."""
    resolved_options = options or TraceOptions()
    result = scan_directory(vault_root)
    vault_files = [Path(f.file_path) for f in result.files]

    content = note_path.read_text(encoding="utf-8")
    links = extract_links(content)
    internal_links = [link for link in links if not link.is_url]

    matched_files = []
    for link in internal_links:
        matched = _resolve_link_to_file(link.target, vault_files)
        if matched:
            matched_files.append(matched)

    matched_set = {str(p) for p in matched_files}
    filtered_files = [f for f in result.files if str(f.file_path) in matched_set]

    total = len(filtered_files)
    with_fm = sum(1 for f in filtered_files if f.frontmatter)
    without_fm = total - with_fm
    errors = sum(1 for f in filtered_files if f.status != "ok")

    return {
        "note_path": str(note_path),
        "vault_root": str(vault_root),
        "options": {
            "follow_chain": resolved_options.follow_chain,
            "max_depth": resolved_options.max_depth,
        },
        "metadata": {
            "source_directory": str(result.metadata.source_directory),
            "total_files": total,
            "files_with_frontmatter": with_fm,
            "files_without_frontmatter": without_fm,
            "errors": errors,
        },
        "files": [
            {
                "file_path": str(f.file_path),
                "frontmatter": f.frontmatter,
                "status": f.status,
                "error": f.error,
                "stats": {
                    "file_size": f.stats.file_size,
                    "modified_time": f.stats.modified_time,
                    "access_time": f.stats.access_time,
                }
                if f.stats
                else None,
                "file_hash": f.file_hash,
            }
            for f in filtered_files
        ],
        "matched_links": [str(p) for p in matched_files],
    }
