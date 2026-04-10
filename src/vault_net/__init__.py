"""Public package surface for vault-net."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from vault_net.models import VaultGraph, VaultGraphMetadata, VaultIndex
from vault_net.scan import scan_vault
from vault_net.vault_digraph import build_note_ego_graph, build_vault_digraph
from vault_net.vault_registry import VaultRegistry
from vault_net.views import build_vault_edge_list

try:
    __version__ = version("vault-net")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = [
    "VaultIndex",
    "VaultGraph",
    "VaultGraphMetadata",
    "VaultRegistry",
    "__version__",
    "build_note_ego_graph",
    "build_vault_digraph",
    "build_vault_edge_list",
    "scan_vault",
]
