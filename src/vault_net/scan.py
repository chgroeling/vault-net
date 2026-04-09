"""Core vault scanning and index-building functions."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog
from matterify import scan_directory
from matterify.constants import BLACKLIST

from vault_net.models import VaultFile, VaultFileStats, VaultIndex, VaultIndexMetadata, VaultLink
from vault_net.utils import _extract_file_links

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from matterify.models import ScanResults


def _extract_file_links_callback(content: str) -> list[VaultLink]:
    """Extract file links from note content as VaultLink objects."""
    return [
        VaultLink(
            link_type=link.link_type,
            target=link.target,
            alias=link.alias,
            heading=link.heading,
            blockid=link.blockid,
        )
        for link in _extract_file_links(content)
    ]


def _convert_scan_to_index(
    vault_root: Path,
    scan_result: ScanResults,
) -> VaultIndex:
    """Convert a matterify scan result to a VaultIndex.

    This internal function transforms matterify's ScanResults into
    our local VaultIndex type, converting FileEntry objects to
    VaultFile and ScanMetadata to VaultIndexMetadata.

    Args:
        vault_root: Root directory of the vault.
        scan_result: ScanResults from matterify.scan_directory().

    Returns:
        VaultIndex with converted file entries and metadata.
    """
    # Convert matterify ScanMetadata to VaultIndexMetadata
    meta = scan_result.metadata
    # These are guaranteed non-None because compute_frontmatter=True
    assert meta.files_with_frontmatter is not None
    assert meta.files_without_frontmatter is not None
    metadata = VaultIndexMetadata(
        root=meta.root,
        total_files=meta.total_files,
        files_with_frontmatter=meta.files_with_frontmatter,
        files_without_frontmatter=meta.files_without_frontmatter,
        errors=meta.errors,
        scan_duration_seconds=meta.scan_duration_seconds,
        avg_duration_per_file_ms=meta.avg_duration_per_file_ms,
        throughput_files_per_second=meta.throughput_files_per_second,
    )

    # Convert matterify FileEntry list to VaultFile list
    files: list[VaultFile] = []
    for entry in scan_result.files:
        # Access custom_data from matterify and convert to VaultLink objects
        raw_links = getattr(entry, "custom_data", None)
        links: list[VaultLink] | None = None
        if isinstance(raw_links, list):
            links = [
                VaultLink(
                    link_type=link["link_type"],
                    target=link["target"],
                    alias=link.get("alias"),
                    heading=link.get("heading"),
                    blockid=link.get("blockid"),
                )
                for link in raw_links
                if isinstance(link, dict)
                and isinstance(link.get("link_type"), str)
                and isinstance(link.get("target"), str)
            ]
            if not links:
                links = None
        # These are guaranteed non-None: compute_frontmatter/compute_stats/compute_hash=True
        assert entry.stats is not None
        assert entry.file_hash is not None
        vault_file = VaultFile(
            file_path=entry.file_path,
            frontmatter=entry.frontmatter,
            status=entry.status,
            error=entry.error,
            stats=VaultFileStats(
                file_size=entry.stats.file_size,
                modified_time=entry.stats.modified_time,
                access_time=entry.stats.access_time,
            ),
            file_hash=entry.file_hash,
            links=links,
        )
        files.append(vault_file)

    return VaultIndex(
        vault_root=vault_root,
        metadata=metadata,
        files=files,
    )


def scan_vault(
    vault_root: Path,
    extra_exclude_dir: tuple[str, ...] = (),
    no_default_excludes: bool = False,
) -> VaultIndex:
    """Scan vault directory and build a VaultIndex.

    Args:
        vault_root: Root directory of the vault.
        extra_exclude: Additional directory names to exclude from traversal,
            added on top of the default exclusions (`.git`, `.obsidian`,
            `__pycache__`, `.venv`, `venv`, `node_modules`, `.mypy_cache`,
            `.pytest_cache`, `.ruff_cache`).
        no_default_excludes: When True, skip the built-in default exclusions
            and use only the entries in `extra_exclude`.

    Returns:
        VaultIndex with scan results and prebuilt lookup maps.
    """
    start = time.monotonic()
    logger.debug("scan_vault.start", vault_root=str(vault_root))

    base = () if no_default_excludes else BLACKLIST
    scan_result = scan_directory(
        vault_root,
        exclude=base + extra_exclude_dir,
        compute_hash=True,
        compute_stats=True,
        compute_frontmatter=True,
        callback=_extract_file_links_callback,
    )

    # Inline build_index logic
    index = _convert_scan_to_index(vault_root, scan_result)
    duration = time.monotonic() - start
    logger.debug(
        "scan_vault.complete",
        duration=round(duration, 4),
        file_count=len(index.files),
    )
    return index


__all__ = [
    "scan_vault",
]
