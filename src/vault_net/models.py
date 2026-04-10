"""Typed models for link resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


@dataclass(frozen=True, slots=True)
class VaultIndexMetadata:
    """Metadata summary for a vault index operation.

    Mirrors matterify.models.ScanMetadata but uses local types.

    Attributes:
        root: Root directory path of the indexed vault.
        total_files: Total number of files scanned.
        files_with_frontmatter: Count of files containing YAML frontmatter.
        files_without_frontmatter: Count of files without YAML frontmatter.
        errors: Number of files that encountered errors during scanning.
        scan_duration_seconds: Total time taken for the scan.
        avg_duration_per_file_ms: Average processing time per file in milliseconds.
        throughput_files_per_second: File processing rate.
    """

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
    """Metadata summary for a vault graph operation.

    Attributes:
        edge_count: Number of resolved graph edges.
    """

    edge_count: int


@dataclass(frozen=True, slots=True)
class VaultFileStats:
    """File statistics for a scanned vault file.

    Mirrors matterify.models.FileStats but uses local types.

    Attributes:
        file_size: File size in bytes, or None if unavailable.
        modified_time: Last modification time as ISO 8601 string, or None.
        access_time: Last access time as ISO 8601 string, or None.
    """

    file_size: int | None
    modified_time: str | None
    access_time: str | None


@dataclass(frozen=True, slots=True)
class VaultGraph:
    """Resolved vault graph representation.

    Attributes:
        vault_root: Root directory of the vault as a Path.
        metadata: Summary metadata about the graph.
        digraph: Resolved directed graph whose nodes are note slugs.
    """

    vault_root: Path
    metadata: VaultGraphMetadata
    digraph: nx.DiGraph[str]


@dataclass(frozen=True, slots=True)
class VaultLink:
    """Represents a serialized obsilink link used in API output."""

    link_type: str
    target: str
    alias: str | None
    heading: str | None
    blockid: str | None

    @classmethod
    def from_obsilink_link(cls, link: Any) -> VaultLink:
        """Build a VaultLink from obsilink Link fields."""
        return cls(
            link_type=link.type.value,
            target=link.target,
            alias=link.alias,
            heading=link.heading,
            blockid=link.blockid,
        )


@dataclass(frozen=True, slots=True)
class VaultFile:
    """Represent lightweight file identity.

    Attributes:
        slug: Unique short identifier for the file.
        file_path: Path to the file relative to the vault root.
    """

    slug: str
    file_path: str


@dataclass(frozen=True, slots=True)
class VaultNote(VaultFile):
    """Represent a scanned note with metadata and extracted links.

    Mirrors matterify.models.FileEntry but uses local types and renames
    custom_data to links.

    Attributes:
        status: Scan status string (e.g., "ok").
        error: Error message if status is not "ok", otherwise None.
        file_hash: Hash of the file contents.
        frontmatter: Extracted YAML frontmatter as a dictionary.
        stats: File statistics object.
        links: Extracted file links from note content.
    """

    status: str
    error: str | None
    file_hash: str
    frontmatter: dict[str, object] | None
    stats: VaultFileStats
    links: list[VaultLink]

    def to_file(self) -> VaultFile:
        """Return this note as a lightweight `VaultFile`."""
        return VaultFile(
            slug=self.slug,
            file_path=self.file_path,
        )


@dataclass(frozen=True, slots=True)
class VaultIndex:
    """Immutable vault index with file entries and metadata.

    Attributes:
        vault_root: Root directory of the vault as a Path.
        metadata: Summary metadata about the indexing operation.
        files: List of scanned vault files.
    """

    vault_root: Path
    metadata: VaultIndexMetadata
    files: list[VaultNote]

    @property
    def source_directory(self) -> str:
        """Return the source directory path from metadata.

        Backwards-compatible alias for metadata.root.
        """
        return self.metadata.root
