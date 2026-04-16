"""Public application facade wiring default adapters to use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.models import (
        NoteLinkTrace,
        NoteShow,
        VaultGraph,
        VaultIndex,
        VaultLink,
    )

from vault_net.application.use_cases.build_full_graph import BuildFullGraphUseCase
from vault_net.application.use_cases.build_neighborhood_graph import BuildNeighborhoodGraphUseCase
from vault_net.application.use_cases.create_note import CreateNoteUseCase
from vault_net.application.use_cases.delete_note import DeleteNoteUseCase
from vault_net.application.use_cases.index_vault import IndexVaultUseCase
from vault_net.application.use_cases.show_note import ShowNoteUseCase
from vault_net.application.use_cases.trace_note_links import TraceNoteLinksUseCase
from vault_net.infrastructure.graph.networkx_graph_builder import NetworkXGraphBuilder
from vault_net.infrastructure.scanner.matterify_scanner import MatterifyVaultScanner


def index_vault(
    vault_root: Path,
    extra_exclude: tuple[str, ...] = (),
    no_default_excludes: bool = False,
) -> tuple[VaultIndex, dict[str, list[VaultLink]]]:
    """Scan vault directory and build a domain index with note links."""
    use_case = IndexVaultUseCase(scanner=MatterifyVaultScanner())
    return use_case.execute(
        vault_root,
        extra_exclude=extra_exclude,
        no_default_excludes=no_default_excludes,
    )


def get_full_graph(
    vault_index: VaultIndex,
    note_links: dict[str, list[VaultLink]],
) -> VaultGraph:
    """Build and return the resolved full-vault graph."""
    use_case = BuildFullGraphUseCase(graph_builder=NetworkXGraphBuilder())
    return use_case.execute(vault_index, note_links)


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
    extra_exclude: tuple[str, ...] = (),
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
        extra_exclude=extra_exclude,
        no_default_excludes=no_default_excludes,
    )


def create_note(
    vault_root: Path,
    name: str,
    *,
    content: str = "",
    force: bool = False,
) -> str:
    """Create a new note in the vault and return its slug."""
    use_case = CreateNoteUseCase(scanner=MatterifyVaultScanner())
    return use_case.execute(vault_root, name, content=content, force=force)


def show_note(
    vault_root: Path,
    note_input: str,
    *,
    extra_exclude: tuple[str, ...] = (),
    no_default_excludes: bool = False,
    include_content: bool = True,
) -> NoteShow:
    """Show detailed information about a note including its links."""
    use_case = ShowNoteUseCase(
        scanner=MatterifyVaultScanner(),
        graph_builder=NetworkXGraphBuilder(),
    )
    return use_case.execute(
        vault_root,
        note_input,
        extra_exclude=extra_exclude,
        no_default_excludes=no_default_excludes,
        include_content=include_content,
    )


def delete_note(
    vault_root: Path,
    note_input: str,
    *,
    extra_exclude: tuple[str, ...] = (),
    no_default_excludes: bool = False,
) -> str:
    """Delete a note from the vault and return its file path."""
    use_case = DeleteNoteUseCase(scanner=MatterifyVaultScanner())
    return use_case.execute(
        vault_root,
        note_input,
        extra_exclude=extra_exclude,
        no_default_excludes=no_default_excludes,
    )
