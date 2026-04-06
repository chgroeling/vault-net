"""Typed models for link tracing results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class TraceOptions:
    """Store traversal options used for a trace request."""

    follow_chain: bool = False
    max_depth: int | None = None


@dataclass(frozen=True, slots=True)
class TraceRequest:
    """Describe the source note and vault for a trace run."""

    note_path: Path
    vault_root: Path
    options: TraceOptions = field(default_factory=TraceOptions)


@dataclass(frozen=True, slots=True)
class FileStats:
    """File system statistics for a traced file."""

    file_size: int
    modified_time: float
    access_time: float


@dataclass(frozen=True, slots=True)
class TracedFile:
    """Represents a file discovered during link tracing."""

    file_path: str
    frontmatter: dict[str, Any]
    status: str
    error: str | None
    stats: FileStats | None
    file_hash: str | None


@dataclass(frozen=True, slots=True)
class TraceMetadata:
    """Metadata summary for a trace result."""

    source_directory: str
    total_files: int
    files_with_frontmatter: int
    files_without_frontmatter: int
    errors: int


@dataclass(frozen=True, slots=True)
class TraceResponse:
    """Complete result of a link trace operation."""

    note_path: str
    vault_root: str
    options: TraceOptions
    metadata: TraceMetadata
    files: list[TracedFile]
    matched_links: list[str]
