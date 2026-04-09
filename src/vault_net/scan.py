"""Core vault scanning and index-building functions."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from matterify import scan_directory
from matterify.constants import BLACKLIST
from obsilink import extract_links

from vault_net.consts import SLUG_LENGTH
from vault_net.models import VaultFile, VaultFileStats, VaultIndex, VaultIndexMetadata, VaultLink

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from matterify.models import ScanResults


def _generate_slug(filename: str, slug_counts: dict[str, int]) -> str:
    """Generate a unique slug for a filename, max SLUG_LENGTH chars.

    If the base slug (first SLUG_LENGTH chars of filename) is already
    used, appends a numeric suffix and shortens the base to fit.

    Args:
        filename: The filename to generate a slug for.
        slug_counts: Dict tracking used slugs and collision counts.

    Returns:
        A unique slug string, at most SLUG_LENGTH characters.
    """
    base_slug = filename[:SLUG_LENGTH]
    slug = base_slug
    count = slug_counts.get(base_slug, 0)
    while slug in slug_counts:
        # Shorten base to make room for _N suffix (e.g., _0, _1)
        suffix = f"_{count}"
        shortened_len = SLUG_LENGTH - len(suffix)
        if shortened_len < 1:
            shortened_len = 1
        shortened_base = base_slug[:shortened_len]
        slug = f"{shortened_base}{suffix}"
        count += 1
    slug_counts[slug] = 0
    slug_counts[base_slug] = count
    return slug


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
    slug_counts: dict[str, int] = {}
    for entry in scan_result.files:
        # Access custom_data from matterify — already list[Link] from the callback
        raw_links = getattr(entry, "custom_data", None) or []

        # These are guaranteed non-None: compute_frontmatter/compute_stats/compute_hash=True
        assert entry.stats is not None
        assert entry.file_hash is not None

        # Generate unique slug from filename (max SLUG_LENGTH chars)
        filename = Path(entry.file_path).name
        slug = _generate_slug(filename, slug_counts)

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
            links=[VaultLink.from_obsilink_link(link) for link in raw_links if link.is_file],
            slug=slug,
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
        callback=extract_links,
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
