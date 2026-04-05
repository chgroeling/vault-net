"""Public API boundary for link tracing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from link_tracer.models import TraceOptions

if TYPE_CHECKING:
    from pathlib import Path


def trace_links(
    note_path: Path,
    vault_root: Path,
    *,
    options: TraceOptions | None = None,
) -> dict[str, Any]:
    """Return a structured placeholder trace response.

    This initialization build wires the API contract but does not implement tracing.
    """
    resolved_options = options or TraceOptions()
    return {
        "note_path": str(note_path),
        "vault_root": str(vault_root),
        "options": {
            "follow_chain": resolved_options.follow_chain,
            "max_depth": resolved_options.max_depth,
        },
        "nodes": [],
        "edges": [],
        "errors": [
            {
                "code": "not_implemented",
                "message": "Tracing logic is not implemented yet.",
            }
        ],
    }
