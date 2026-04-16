"""Public package surface for vault-net."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from vault_net.application.api import (
    get_full_graph,
    get_neighborhood_graph,
    index_vault,
    trace_note_links,
)
from vault_net.domain.models import NoteLinkTrace, VaultGraph, VaultGraphMetadata, VaultIndex
from vault_net.domain.services.vault_registry import VaultRegistry
from vault_net.interface.formatters.views import build_vault_edge_list

try:
    __version__ = version("vault-net")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = [
    "NoteLinkTrace",
    "VaultIndex",
    "VaultGraph",
    "VaultGraphMetadata",
    "VaultRegistry",
    "__version__",
    "build_vault_edge_list",
    "get_full_graph",
    "get_neighborhood_graph",
    "index_vault",
    "trace_note_links",
]
