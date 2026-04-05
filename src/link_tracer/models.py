"""Typed models for link tracing results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class TraceOptions:
    """Store traversal options used for a trace request."""

    follow_chain: bool = False
    max_depth: int | None = None


@dataclass(frozen=True, slots=True)
class TraceRequest:
    """Describe the source note and vault for a trace run."""

    note_path: Path
    vault_root: Path
    options: TraceOptions = field(default_factory=TraceOptions)
