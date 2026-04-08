"""Public API boundary for link resolution."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog
from matterify import scan_directory

from link_tracer.models import ResolveResponse, ResolveVaultResponse, VaultIndex
from link_tracer.resolve_links import resolve_links
from link_tracer.resolve_vault_links import (
    _extract_file_links_callback,
    _resolve_link_to_file,
    resolve_vault_links,
)

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from matterify.models import AggregatedResult


def build_vault_index(  # type: ignore[no-any-unimported]
    vault_root: Path,
    scan_result: AggregatedResult,
) -> VaultIndex:
    """Build a VaultIndex from an existing scan result.

    Args:
        vault_root: Root directory of the vault.
        scan_result: AggregatedResult from matterify.scan_directory().

    Returns:
        VaultIndex with prebuilt lookup maps.
    """
    start = time.monotonic()
    logger.debug("build_vault_index.start")

    index = VaultIndex.from_scan_result(vault_root, scan_result)

    duration = time.monotonic() - start
    logger.debug(
        "build_vault_index.complete",
        duration=round(duration, 4),
        file_count=len(index.files),
    )
    return index


def scan_vault(vault_root: Path) -> VaultIndex:
    """Scan vault directory and build a VaultIndex.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        VaultIndex with scan results and prebuilt lookup maps.
    """
    start = time.monotonic()
    logger.debug("scan_vault.start", vault_root=str(vault_root))

    scan_result = scan_directory(vault_root, callback=_extract_file_links_callback)
    index = build_vault_index(vault_root, scan_result)

    duration = time.monotonic() - start
    logger.debug(
        "scan_vault.complete",
        duration=round(duration, 4),
        file_count=len(index.files),
    )
    return index


__all__ = [
    "ResolveResponse",
    "ResolveVaultResponse",
    "build_vault_index",
    "resolve_links",
    "resolve_vault_links",
    "scan_vault",
    "_resolve_link_to_file",
]
