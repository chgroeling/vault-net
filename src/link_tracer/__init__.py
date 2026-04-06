"""Public package surface for link-tracer."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from link_tracer.api import build_vault_context, resolve_links, scan_vault
from link_tracer.models import ResolveOptions, ResolveResponse, VaultIndex

try:
    __version__ = version("link-tracer")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "ResolveOptions",
    "ResolveResponse",
    "VaultIndex",
    "__version__",
    "build_vault_context",
    "resolve_links",
    "scan_vault",
]
