"""Matterify-backed implementation of the vault scanner port."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import structlog
from matterify import scan_directory
from matterify.constants import DEFAULT_EXCLUDE_PATTERNS
from obsilink import extract_links

from vault_net.domain.models import (
    VaultFile,
    VaultFileStats,
    VaultIndex,
    VaultIndexMetadata,
    VaultLink,
    VaultListing,
    VaultNote,
)
from vault_net.domain.services.slug_service import generate_slug

if TYPE_CHECKING:
    from matterify.models import FileStats, ScanResults

logger = structlog.get_logger(__name__)


def _to_vault_link(link: Any) -> VaultLink:
    """Convert an obsilink link object into a domain `VaultLink`."""
    return VaultLink(
        link_type=link.type.value,
        target=link.target,
        alias=link.alias,
        heading=link.heading,
        blockid=link.blockid,
    )


def _convert_scan_to_index(
    vault_root: Path,
    scan_result: ScanResults,
) -> tuple[VaultIndex, dict[str, list[VaultLink]]]:
    """Convert a matterify scan result to a `VaultIndex` and note links dict."""
    meta = scan_result.metadata
    files_with_frontmatter = cast("int", meta.files_with_frontmatter)
    files_without_frontmatter = cast("int", meta.files_without_frontmatter)
    metadata = VaultIndexMetadata(
        root=str(meta.root),
        total_files=meta.total_files,
        files_with_frontmatter=files_with_frontmatter,
        files_without_frontmatter=files_without_frontmatter,
        errors=meta.errors,
        scan_duration_seconds=meta.scan_duration_seconds,
        avg_duration_per_file_ms=meta.avg_duration_per_file_ms,
        throughput_files_per_second=meta.throughput_files_per_second,
    )

    files: list[VaultNote] = []
    note_links: dict[str, list[VaultLink]] = {}
    slug_counts: dict[str, int] = {}
    for entry in scan_result.files:
        raw_links = getattr(entry, "custom_data", None) or []
        entry_stats = cast("FileStats", entry.stats)
        entry_hash = cast("str", entry.file_hash)

        file_path_str = str(entry.file_path)
        filename = Path(file_path_str).name
        slug = generate_slug(filename, slug_counts)
        note = VaultNote(
            file_path=file_path_str,
            frontmatter=entry.frontmatter,
            status=entry.status.value,
            error=entry.error.value if entry.error else None,
            stats=VaultFileStats(
                file_size=entry_stats.file_size,
                modified_time=entry_stats.modified_time,
                access_time=entry_stats.access_time,
            ),
            file_hash=entry_hash,
            slug=slug,
        )
        note_link_list = [_to_vault_link(link) for link in raw_links if link.is_file]
        if note_link_list:
            note_links[note.slug] = note_link_list
        files.append(note)

    vault_index = VaultIndex(vault_root=vault_root, metadata=metadata, files=files)
    return vault_index, note_links


def _convert_scan_to_listing(
    vault_root: Path,
    scan_result: ScanResults,
) -> VaultListing:
    """Convert a matterify scan result to a lightweight `VaultListing`."""
    files: list[VaultFile] = []
    slug_counts: dict[str, int] = {}
    for entry in scan_result.files:
        file_path_str = str(entry.file_path)
        filename = Path(file_path_str).name
        slug = generate_slug(filename, slug_counts)
        files.append(VaultFile(slug=slug, file_path=file_path_str))
    return VaultListing(vault_root=vault_root, files=files)


class MatterifyVaultScanner:
    """Scanner adapter that uses matterify and obsilink."""

    def scan(
        self,
        vault_root: Path,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> tuple[VaultIndex, dict[str, list[VaultLink]]]:
        """Scan vault directory and build a domain index with note links.

        Args:
            vault_root: Root directory of the vault to scan.
            extra_exclude: Additional glob patterns to exclude from traversal
                (e.g., ".temp", "**/drafts"). These are passed to the scanner's
                exclude parameter alongside any default exclusion patterns.
            no_default_excludes: If True, exclude only the extra patterns provided.
                If False (default), also apply built-in default exclusion patterns
                (e.g., "**/.git", "**/.obsidian").
        """
        start = time.monotonic()
        logger.debug("scan_vault.start", vault_root=str(vault_root))

        base = () if no_default_excludes else DEFAULT_EXCLUDE_PATTERNS
        scan_result = scan_directory(
            vault_root,
            exclude=base + extra_exclude,
            compute_hash=True,
            compute_stats=True,
            compute_frontmatter=True,
            callback=extract_links,
        )

        index, note_links = _convert_scan_to_index(vault_root, scan_result)
        duration = time.monotonic() - start
        logger.debug(
            "scan_vault.complete",
            duration=round(duration, 4),
            file_count=len(index.files),
        )
        return index, note_links

    def index_files(
        self,
        vault_root: Path,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> VaultListing:
        """Index vault files into a lightweight listing of slugs and paths."""
        start = time.monotonic()
        logger.debug("index_files.start", vault_root=str(vault_root))

        base = () if no_default_excludes else DEFAULT_EXCLUDE_PATTERNS
        scan_result = scan_directory(
            vault_root,
            exclude=base + extra_exclude,
            compute_hash=False,
            compute_stats=False,
            compute_frontmatter=True,
            callback=None,
        )

        listing = _convert_scan_to_listing(vault_root, scan_result)
        duration = time.monotonic() - start
        logger.debug(
            "index_files.complete",
            duration=round(duration, 4),
            file_count=len(listing.files),
        )
        return listing
