"""Public API boundary for link tracing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from matterify import scan_directory

from link_tracer.models import TraceOptions

if TYPE_CHECKING:
    from pathlib import Path


def trace_links(
    note_path: Path,
    vault_root: Path,
    *,
    options: TraceOptions | None = None,
) -> dict[str, Any]:
    """Scan vault directory and return structured trace response."""
    resolved_options = options or TraceOptions()
    result = scan_directory(vault_root)
    return {
        "note_path": str(note_path),
        "vault_root": str(vault_root),
        "options": {
            "follow_chain": resolved_options.follow_chain,
            "max_depth": resolved_options.max_depth,
        },
        "metadata": {
            "source_directory": str(result.metadata.source_directory),
            "total_files": result.metadata.total_files,
            "files_with_frontmatter": result.metadata.files_with_frontmatter,
            "files_without_frontmatter": result.metadata.files_without_frontmatter,
            "errors": result.metadata.errors,
            "scan_duration_seconds": result.metadata.scan_duration_seconds,
            "avg_duration_per_file_ms": result.metadata.avg_duration_per_file_ms,
            "throughput_files_per_second": result.metadata.throughput_files_per_second,
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
            for f in result.files
        ],
    }
