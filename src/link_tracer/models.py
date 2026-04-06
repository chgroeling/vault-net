"""Typed models for link resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from matterify.models import FileEntry


@dataclass(frozen=True, slots=True)
class ResolveOptions:
    """Store traversal options used for a resolve request."""

    follow_chain: bool = False
    max_depth: int | None = None


@dataclass(frozen=True, slots=True)
class FileStats:
    """File system statistics for a resolved file."""

    file_size: int
    modified_time: float
    access_time: float


@dataclass(frozen=True, slots=True)
class ResolvedFile:
    """Represents a file discovered during link resolution."""

    file_path: str
    frontmatter: dict[str, Any]
    status: str
    error: str | None
    stats: FileStats | None
    file_hash: str | None


@dataclass(frozen=True, slots=True)
class ResolveMetadata:
    """Metadata summary for a resolution result."""

    source_directory: str
    total_files: int
    files_with_frontmatter: int
    files_without_frontmatter: int
    errors: int


@dataclass(frozen=True, slots=True)
class ResolveResponse:
    """Complete result of a link resolution operation."""

    vault_root: str
    options: ResolveOptions
    metadata: ResolveMetadata
    files: list[ResolvedFile]
    matched_links: list[str]


@dataclass(frozen=True, slots=True)
class VaultIndex:  # type: ignore[no-any-unimported]
    """Immutable vault index with prebuilt lookup maps."""

    vault_root: Path
    files: list[FileEntry]  # type: ignore[no-any-unimported]
    source_directory: str
    name_to_file: dict[str, Path]
    stem_to_file: dict[str, Path]
    relative_path_to_file: dict[str, Path]
