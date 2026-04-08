"""Typed models for link resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from link_tracer.utils import _normalize_lookup_key

if TYPE_CHECKING:
    from matterify.models import AggregatedResult, FileEntry


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
class ResolveMetadata:
    """Metadata summary for a resolution result."""

    source_directory: str
    total_files: int
    files_with_frontmatter: int
    files_without_frontmatter: int
    errors: int


@dataclass(frozen=True, slots=True)
class VaultGraph:
    """Vault-wide link graph: edges between notes with summary metadata."""

    vault_root: str
    metadata: ResolveMetadata
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

    @staticmethod
    def _build_vault_lookups(
        vault_files: list[Path],
    ) -> tuple[dict[str, Path], dict[str, Path], dict[str, Path]]:
        """Build case-insensitive lookup maps for vault files."""
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
        name_to_file, stem_to_file, relative_path_to_file = cls._build_vault_lookups(vault_files)

        source_directory = getattr(scan_result.metadata, "source_directory", None)
        if source_directory is None:
            source_directory = scan_result.metadata.root

        return cls(
            vault_root=vault_root,
            files=scan_result.files,
            source_directory=str(source_directory),
            name_to_file=name_to_file,
            stem_to_file=stem_to_file,
            relative_path_to_file=relative_path_to_file,
        )
