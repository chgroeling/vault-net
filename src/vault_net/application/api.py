"""Public application facade wiring default adapters to use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.models import NoteLinkTrace, NoteShow, VaultGraph, VaultIndex

from vault_net.application.use_cases.build_full_graph import BuildFullGraphUseCase
from vault_net.application.use_cases.build_neighborhood_graph import BuildNeighborhoodGraphUseCase
from vault_net.application.use_cases.scan_vault import ScanVaultUseCase
from vault_net.application.use_cases.show_note import ShowNoteUseCase
from vault_net.application.use_cases.trace_note_links import TraceNoteLinksUseCase
from vault_net.infrastructure.graph.networkx_graph_builder import NetworkXGraphBuilder
from vault_net.infrastructure.scanner.matterify_scanner import MatterifyVaultScanner


def scan_vault(
    vault_root: Path,
    extra_exclude_dir: tuple[str, ...] = (),
    no_default_excludes: bool = False,
) -> VaultIndex:
    """Scan vault directory and build a domain index."""
    use_case = ScanVaultUseCase(scanner=MatterifyVaultScanner())
    return use_case.execute(
        vault_root,
        extra_exclude_dir=extra_exclude_dir,
        no_default_excludes=no_default_excludes,
    )


def get_full_graph(vault_index: VaultIndex) -> VaultGraph:
    """Build and return the resolved full-vault graph."""
    use_case = BuildFullGraphUseCase(graph_builder=NetworkXGraphBuilder())
    return use_case.execute(vault_index)


def get_neighborhood_graph(
    source_slug: str,
    graph: VaultGraph,
    *,
    depth: int = 1,
) -> VaultGraph:
    """Return the directed neighborhood graph around `source_slug`."""
    use_case = BuildNeighborhoodGraphUseCase(graph_builder=NetworkXGraphBuilder())
    return use_case.execute(source_slug, graph, depth=depth)


def trace_note_links(
    vault_root: Path,
    note_input: str,
    *,
    depth: int = 1,
    extra_exclude_dir: tuple[str, ...] = (),
    no_default_excludes: bool = False,
) -> NoteLinkTrace:
    """Trace links from a note, returning the neighborhood graph and index."""
    use_case = TraceNoteLinksUseCase(
        scanner=MatterifyVaultScanner(),
        graph_builder=NetworkXGraphBuilder(),
    )
    return use_case.execute(
        vault_root,
        note_input,
        depth=depth,
        extra_exclude_dir=extra_exclude_dir,
        no_default_excludes=no_default_excludes,
    )


def show_note(
    vault_root: Path,
    note_input: str,
    *,
    extra_exclude_dir: tuple[str, ...] = (),
    no_default_excludes: bool = False,
) -> NoteShow:
    """Show detailed information about a note including its links."""
    use_case = ShowNoteUseCase(
        scanner=MatterifyVaultScanner(),
        graph_builder=NetworkXGraphBuilder(),
    )
    return use_case.execute(
        vault_root,
        note_input,
        extra_exclude_dir=extra_exclude_dir,
        no_default_excludes=no_default_excludes,
    )
