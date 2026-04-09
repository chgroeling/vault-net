"""Typed models for link resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
class VaultFile:
    """Represents a scanned file in the vault.

    Mirrors matterify.models.FileEntry but uses local types and
    renames custom_data to links.

    Attributes:
        file_path: Path to the file relative to the vault root.
        frontmatter: Extracted YAML frontmatter as a dictionary.
        status: Scan status string (e.g., "ok").
        error: Error message if status is not "ok", otherwise None.
        stats: Optional file statistics object.
        file_hash: Optional hash of the file contents.
        links: Optional list of extracted links from the file content.
            Renamed from custom_data in matterify.
    """

    file_path: str
    frontmatter: dict
    status: str
    error: str | None
    stats: object | None
    file_hash: str | None
    links: list[VaultLink] | None


@dataclass(frozen=True, slots=True)
class VaultLink:
    """Represents a serialized obsilink link used in API output."""

    link_type: str
    target: str
    alias: str | None
    heading: str | None
    blockid: str | None

    @classmethod
    def from_obsilink_link(
        cls,
        *,
        link_type: str,
        target: str,
        alias: str | None,
        heading: str | None,
        blockid: str | None,
    ) -> VaultLink:
        """Build a VaultLink from obsilink Link fields."""
        return cls(
            link_type=link_type,
            target=target,
            alias=alias,
            heading=heading,
            blockid=blockid,
        )


@dataclass(frozen=True, slots=True)
class LinkEdge:
    """Represents a directed edge from one note to a link target."""

    link: VaultLink
    resolved: bool
    target_note: str | None = None
    unresolved_reason: str | None = None


@dataclass(frozen=True, slots=True)
class VaultGraphMetadata:
    """Metadata summary for a vault graph result."""

    source_directory: str
    total_files: int
    errors: int


@dataclass(frozen=True, slots=True)
class VaultGraph:
    """Vault-wide link graph: edges between notes with summary metadata."""

    vault_root: str
    metadata: VaultGraphMetadata
    edges: dict[str, list[LinkEdge]]


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
    files: list[VaultFile]

    @property
    def source_directory(self) -> str:
        """Return the source directory path from metadata.

        Backwards-compatible alias for metadata.root.
        """
        return self.metadata.root
