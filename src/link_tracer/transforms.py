"""Graph transform functions for alternative output representations."""

from __future__ import annotations

from collections import deque

from link_tracer.models import LayerEntry, VaultGraph, VaultLayered

__all__ = ["to_layered"]


def to_layered(source_note: str, graph: VaultGraph) -> VaultLayered:
    """Transform a note graph into a flat BFS depth-layer list.

    Each note in the graph is assigned to its shallowest reachable depth from
    `source_note`. Both outgoing edges and backlinks are traversed, matching
    the bidirectional structure produced by `build_note_graph`.

    Args:
        source_note: Vault-relative path of the origin note (depth 0).
        graph: Scoped `VaultGraph` returned by `build_note_graph`.

    Returns:
        `VaultLayered` with a flat `layers` list ordered by traversal depth.
    """
    # Build reverse index: target_note → list of notes that link to it
    reverse: dict[str, list[str]] = {}
    for src, edges in graph.edges.items():
        for edge in edges:
            if edge.resolved and edge.target_note is not None:
                reverse.setdefault(edge.target_note, []).append(src)

    seen: set[str] = {source_note}
    queue: deque[tuple[str, int]] = deque([(source_note, 0)])
    entries: list[LayerEntry] = []

    while queue:
        note, depth = queue.popleft()
        entries.append(LayerEntry(depth=depth, note=note))

        # Forward neighbours: notes this note links to
        for edge in graph.edges.get(note, []):
            if edge.resolved and edge.target_note is not None:
                neighbour = edge.target_note
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append((neighbour, depth + 1))

        # Backward neighbours: notes that link to this note
        for src in reverse.get(note, []):
            if src not in seen:
                seen.add(src)
                queue.append((src, depth + 1))

    return VaultLayered(
        source_note=source_note,
        vault_root=graph.vault_root,
        metadata=graph.metadata,
        layers=entries,
    )
