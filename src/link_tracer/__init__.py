"""Public package surface for link-tracer."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from link_tracer.api import trace_links

try:
    __version__ = version("link-tracer")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__", "trace_links"]
