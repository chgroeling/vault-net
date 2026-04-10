"""Public package surface for vault-net."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from vault_net.models import NoteGraph, VaultGraph, VaultIndex
from vault_net.note_graph import build_note_graph
from vault_net.scan import scan_vault
from vault_net.vault_edge_list import build_vault_edge_list
from vault_net.vault_graph import build_vault_graph

try:
    __version__ = version("vault-net")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = [
    "NoteGraph",
    "VaultGraph",
    "VaultIndex",
    "__version__",
    "build_note_graph",
    "build_vault_edge_list",
    "build_vault_graph",
    "scan_vault",
]
