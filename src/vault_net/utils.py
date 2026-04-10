"""Shared helpers for link resolution modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from obsilink import extract_links

from vault_net.models import VaultLink

if TYPE_CHECKING:
    from pathlib import Path


def _normalize_lookup_key(path: Path) -> str:
    """Return a case-insensitive normalized lookup key for paths."""
    return path.as_posix().lstrip("./").lower()


def _extract_file_links(content: str) -> list[VaultLink]:
    """Extract file-like links from note content as serializable models."""
    links = extract_links(content)
    return [VaultLink.from_obsilink_link(link) for link in links if link.is_file]


def _path_for_response(path: Path, resolved_vault: Path) -> str:
    """Return a response-safe path string relative to vault when possible."""
    resolved_path = path.resolve()
    try:
        return str(resolved_path.relative_to(resolved_vault))
    except ValueError:
        return str(resolved_path)
