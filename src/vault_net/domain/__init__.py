"""Domain layer: entities, ports, and pure services."""

from vault_net.domain.models import (
    NoteLinkTrace,
    VaultFile,
    VaultFileStats,
    VaultGraph,
    VaultGraphMetadata,
    VaultIndex,
    VaultIndexMetadata,
    VaultLink,
    VaultListing,
    VaultNote,
)
from vault_net.domain.protocols import GraphBuilder, VaultScanner
from vault_net.domain.services.vault_registry import VaultFileLookup, VaultRegistry

__all__ = [
    "GraphBuilder",
    "NoteLinkTrace",
    "VaultFile",
    "VaultFileLookup",
    "VaultFileStats",
    "VaultGraph",
    "VaultGraphMetadata",
    "VaultIndex",
    "VaultIndexMetadata",
    "VaultLink",
    "VaultListing",
    "VaultNote",
    "VaultRegistry",
    "VaultScanner",
]
