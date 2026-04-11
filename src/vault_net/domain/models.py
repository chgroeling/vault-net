"""Typed domain models for vault indexing and graph resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.protocols import VaultDiGraph


@dataclass(frozen=True, slots=True)
class VaultIndexMetadata:
    """Metadata summary for a vault index operation."""

    root: str
    total_files: int
    files_with_frontmatter: int
    files_without_frontmatter: int
    errors: int
    scan_duration_seconds: float
    avg_duration_per_file_ms: float
    throughput_files_per_second: float


@dataclass(frozen=True, slots=True)
class VaultGraphMetadata:
    """Metadata summary for a vault graph operation."""

    edge_count: int


@dataclass(frozen=True, slots=True)
class VaultFileStats:
    """File statistics for a scanned vault file."""

    file_size: int | None
    modified_time: str | None
    access_time: str | None


@dataclass(frozen=True, slots=True)
class VaultGraph:
    """Resolved vault graph representation."""

    vault_root: Path
    metadata: VaultGraphMetadata
    digraph: VaultDiGraph


@dataclass(frozen=True, slots=True)
class VaultLink:
    """Serialized link model used throughout the domain."""

    link_type: str
    target: str
    alias: str | None
    heading: str | None
    blockid: str | None


@dataclass(frozen=True, slots=True)
class VaultFile:
    """Lightweight identity for a file in the vault."""

    slug: str
    file_path: str


@dataclass(frozen=True, slots=True)
class VaultNote(VaultFile):
    """Scanned note with metadata and extracted links."""

    status: str
    error: str | None
    file_hash: str
    frontmatter: dict[str, object] | None
    stats: VaultFileStats
    links: list[VaultLink]

    def to_file(self) -> VaultFile:
        """Return this note as a lightweight file identity."""
        return VaultFile(slug=self.slug, file_path=self.file_path)


@dataclass(frozen=True, slots=True)
class VaultIndex:
    """Immutable vault index with file entries and metadata."""

    vault_root: Path
    metadata: VaultIndexMetadata
    files: list[VaultNote]

    @property
    def source_directory(self) -> str:
        """Return source directory path from metadata."""
        return self.metadata.root


@dataclass(frozen=True, slots=True)
class NoteLinkTrace:
    """Result of tracing links from a single note."""

    source_slug: str
    vault_index: VaultIndex
    neighborhood_graph: VaultGraph


@dataclass(frozen=True, slots=True)
class NoteShow:
    """Result of showing a note with its links."""

    note: VaultNote
    forward_links: list[VaultFile]
    backward_links: list[VaultFile]


class InputError(Exception):
    """Raised when a note input (file path or slug) cannot be resolved."""
