"""Public package surface for link-tracer."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from link_tracer.scan import build_index, scan_vault
from link_tracer.models import ResolveOptions, VaultGraph, VaultIndex
from link_tracer.note_graph import build_note_graph
from link_tracer.vault_graph import build_vault_graph

try:
    __version__ = version("link-tracer")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = [
    "ResolveOptions",
    "VaultGraph",
    "VaultIndex",
    "__version__",
    "build_index",
    "build_note_graph",
    "build_vault_graph",
    "scan_vault",
]
