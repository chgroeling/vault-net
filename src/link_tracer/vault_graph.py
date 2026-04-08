"""Vault-wide link resolution implementation."""

from __future__ import annotations

import time
from pathlib import Path

import structlog

from link_tracer.models import (
    ExtractedLink,
    LinkEdge,
    ResolvedFile,
    ResolveMetadata,
    VaultGraph,
    VaultIndex,
)
from link_tracer.utils import _extract_file_links, _normalize_lookup_key, _path_for_response
from link_tracer.consts import _FILE_LINKS_KEY, _POSSIBLE_EXTENSIONS

logger = structlog.get_logger(__name__)

def _entry_has_file_links_payload(entry: object) -> bool:
    """Return whether an entry contains a serialized file-links payload."""
    custom_data = getattr(entry, "custom_data", None)
    return isinstance(custom_data, dict) and isinstance(custom_data.get(_FILE_LINKS_KEY), list)

def _entry_file_links(entry: object) -> list[ExtractedLink]:
    """Read serialized file links from a scan entry custom_data payload."""
    custom_data = getattr(entry, "custom_data", None)
    if not isinstance(custom_data, dict):
        return []

    raw_links = custom_data.get(_FILE_LINKS_KEY)
    if not isinstance(raw_links, list):
        return []

    links: list[ExtractedLink] = []
    for raw_link in raw_links:
        if not isinstance(raw_link, dict):
            continue

        link_type_raw = raw_link.get("link_type")
        target_raw = raw_link.get("target")
        alias_raw = raw_link.get("alias")
        heading_raw = raw_link.get("heading")
        blockid_raw = raw_link.get("blockid")

        if not isinstance(link_type_raw, str) or not isinstance(target_raw, str):
            continue

        alias = alias_raw if isinstance(alias_raw, str) else None
        heading = heading_raw if isinstance(heading_raw, str) else None
        blockid = blockid_raw if isinstance(blockid_raw, str) else None

        links.append(
            ExtractedLink.from_obsilink_link(
                link_type=link_type_raw,
                target=target_raw,
                alias=alias,
                heading=heading,
                blockid=blockid,
            )
        )

    return links


def _resolve_link_to_file(
    link_path: Path,
    vault_index: VaultIndex,
) -> Path | None:
    """Resolve a file-like link target to a scanned vault file."""
    target_str = str(link_path).strip()

    if not target_str:
        return None

    target_path = Path(target_str)
    target_key = _normalize_lookup_key(target_path)

    path_match = vault_index.relative_path_to_file.get(target_key)
    if path_match:
        return path_match

    direct_match = vault_index.name_to_file.get(target_path.name.lower())
    if direct_match:
        return direct_match

    for ext in _POSSIBLE_EXTENSIONS:
        candidate = (
            target_path.with_suffix(ext) if target_path.suffix else Path(f"{target_str}{ext}")
        )
        candidate_path_match = vault_index.relative_path_to_file.get(
            _normalize_lookup_key(candidate)
        )
        if candidate_path_match:
            return candidate_path_match

        candidate_match = vault_index.name_to_file.get(candidate.name.lower())
        if candidate_match:
            return candidate_match

    return vault_index.stem_to_file.get(target_path.stem.lower())


def _resolve_extracted_link(
    extracted_link: ExtractedLink,
    vault_index: VaultIndex,
    resolved_vault: Path,
) -> tuple[LinkEdge, Path | None]:
    """Resolve one extracted link into an edge and optional target path."""
    matched = _resolve_link_to_file(Path(extracted_link.target), vault_index)
    if matched is None:
        return (
            LinkEdge(
                link=extracted_link,
                resolved=False,
                target_note=None,
                unresolved_reason="not_found",
            ),
            None,
        )

    resolved_target = (resolved_vault / matched).resolve()
    return (
        LinkEdge(
            link=extracted_link,
            resolved=True,
            target_note=_path_for_response(resolved_target, resolved_vault),
        ),
        resolved_target,
    )


def build_vault_graph(vault_index: VaultIndex) -> VaultGraph:
    """Resolve all file links for every scanned note in a vault."""
    start = time.monotonic()
    logger.debug("build_vault_graph.start", total_files=len(vault_index.files))

    resolved_vault = vault_index.vault_root.resolve()
    edges: dict[str, list[LinkEdge]] = {}

    for entry in vault_index.files:
        source_note_path = (resolved_vault / Path(entry.file_path)).resolve()
        source_note = _path_for_response(source_note_path, resolved_vault)
        if _entry_has_file_links_payload(entry):
            extracted_links = _entry_file_links(entry)
        else:
            content = source_note_path.read_text(encoding="utf-8")
            extracted_links = _extract_file_links(content)

        outgoing_links: list[LinkEdge] = []

        for extracted_link in extracted_links:
            edge, _ = _resolve_extracted_link(extracted_link, vault_index, resolved_vault)
            outgoing_links.append(edge)

        if outgoing_links:
            edges[source_note] = outgoing_links

    resolved_files = [ResolvedFile.from_file_entry(file_entry) for file_entry in vault_index.files]
    metadata = ResolveMetadata.from_files(vault_index.source_directory, resolved_files)
    response = VaultGraph(
        vault_root=str(vault_index.vault_root),
        metadata=metadata,
        edges=edges,
    )

    duration = time.monotonic() - start
    logger.debug(
        "build_vault_graph.complete",
        duration=round(duration, 4),
        files=response.metadata.total_files,
        edges=len(response.edges),
    )
    return response
