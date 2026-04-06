"""Typed models for link resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matterify.models import AggregatedResult, FileEntry


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


@dataclass(frozen=True, slots=True)
class ResolveOptions:
    """Store traversal options used for a resolve request."""

    depth: int = 1

    def __post_init__(self) -> None:
        if self.depth < 0:
            raise ValueError(f"depth must be >= 0, got {self.depth}")


@dataclass(frozen=True, slots=True)
class FileStats:
    """File system statistics for a resolved file."""

    file_size: int
    modified_time: float
    access_time: float


@dataclass(frozen=True, slots=True)
class ExtractedLink:
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
    ) -> ExtractedLink:
        """Build an ExtractedLink from obsilink Link fields."""
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

    link: ExtractedLink
    resolved: bool
    target_note: str | None = None
    unresolved_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedFile:
    """Represents a file discovered during link resolution."""

    file_path: str
    frontmatter: dict[str, Any]
    status: str
    error: str | None
    stats: FileStats | None
    file_hash: str | None

    @classmethod
    def from_file_entry(cls, entry: FileEntry) -> ResolvedFile:  # type: ignore[no-any-unimported]
        """Create a ResolvedFile from a matterify FileEntry."""
        return cls(
            file_path=str(entry.file_path),
            frontmatter=entry.frontmatter,
            status=entry.status,
            error=entry.error,
            stats=FileStats(
                file_size=entry.stats.file_size,
                modified_time=entry.stats.modified_time,
                access_time=entry.stats.access_time,
            )
            if entry.stats
            else None,
            file_hash=entry.file_hash,
        )


@dataclass(frozen=True, slots=True)
class ResolveMetadata:
    """Metadata summary for a resolution result."""

    source_directory: str
    total_files: int
    files_with_frontmatter: int
    files_without_frontmatter: int
    errors: int

    @classmethod
    def from_files(cls, source_directory: str, files: list[ResolvedFile]) -> ResolveMetadata:
        """Build ResolveMetadata from a list of resolved files."""
        total = len(files)
        with_fm = sum(1 for f in files if f.frontmatter)
        return cls(
            source_directory=source_directory,
            total_files=total,
            files_with_frontmatter=with_fm,
            files_without_frontmatter=total - with_fm,
            errors=sum(1 for f in files if f.status != "ok"),
        )


@dataclass(frozen=True, slots=True)
class ResolveResponse:
    """Complete result of a link resolution operation."""

    vault_root: str
    source_note: str
    options: ResolveOptions
    metadata: ResolveMetadata
    files: list[ResolvedFile]
    edges: dict[str, list[LinkEdge]]


@dataclass(frozen=True, slots=True)
class VaultIndex:  # type: ignore[no-any-unimported]
    """Immutable vault index with prebuilt lookup maps."""

    vault_root: Path
    files: list[FileEntry]  # type: ignore[no-any-unimported]
    source_directory: str
    name_to_file: dict[str, Path]
    stem_to_file: dict[str, Path]
    relative_path_to_file: dict[str, Path]

    @classmethod
    def from_scan_result(  # type: ignore[no-any-unimported]
        cls,
        vault_root: Path,
        scan_result: AggregatedResult,
    ) -> VaultIndex:
        """Build a VaultIndex from a matterify scan result.

        Args:
            vault_root: Root directory of the vault.
            scan_result: AggregatedResult from matterify.scan_directory().

        Returns:
            VaultIndex with prebuilt lookup maps.
        """
        vault_files = [Path(f.file_path) for f in scan_result.files]
        name_to_file, stem_to_file, relative_path_to_file = _build_vault_lookups(vault_files)

        return cls(
            vault_root=vault_root,
            files=scan_result.files,
            source_directory=str(scan_result.metadata.source_directory),
            name_to_file=name_to_file,
            stem_to_file=stem_to_file,
            relative_path_to_file=relative_path_to_file,
        )
