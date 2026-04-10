"""Public package surface for vault-net."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from vault_net.models import VaultGraph, VaultGraphMetadata, VaultIndex
from vault_net.scan import scan_vault
from vault_net.transforms import build_vault_edge_list
from vault_net.vault_digraph import build_note_ego_graph, build_vault_digraph
from vault_net.vault_registry import VaultRegistry

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
