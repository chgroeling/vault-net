"""Core vault scanning and index-building functions."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog
from matterify import scan_directory

from link_tracer.models import VaultIndex
from link_tracer.utils import _extract_file_links
from link_tracer.consts import _FILE_LINKS_KEY

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path
    from matterify.models import AggregatedResult

def _extract_file_links_callback(content: str) -> dict[str, object]:
    """Extract serializable file links from note content."""
    file_links = [
        {
            "link_type": link.link_type,
            "target": link.target,
            "alias": link.alias,
            "heading": link.heading,
            "blockid": link.blockid,
        }
        for link in _extract_file_links(content)
    ]
    return {_FILE_LINKS_KEY: file_links}

def build_index(  # type: ignore[no-any-unimported]
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
    logger.debug("build_vault_graph.start")

    index = VaultIndex.from_scan_result(vault_root, scan_result)

    duration = time.monotonic() - start
    logger.debug(
        "build_vault_graph.complete",
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
    index = build_index(vault_root, scan_result)

    duration = time.monotonic() - start
    logger.debug(
        "scan_vault.complete",
        duration=round(duration, 4),
        file_count=len(index.files),
    )
    return index


__all__ = [
    "build_index",
    "scan_vault",
]
