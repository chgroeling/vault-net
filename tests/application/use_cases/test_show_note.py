"""Tests for ShowNoteUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vault_net.application.use_cases.show_note import ShowNoteUseCase
from vault_net.domain.models import NoteShow, VaultFile, VaultGraph, VaultIndex, VaultNote


class TestShowNoteUseCase:
    """Verify ShowNoteUseCase orchestration."""

    def test_execute_orchestrates_scan_then_build_full(self, tmp_path: Path) -> None:
        """Verify scan -> build_full_graph call order."""
        mock_scanner = MagicMock()
        mock_graph_builder = MagicMock()

        mock_vault_index = MagicMock(spec=VaultIndex)
        mock_full_graph = MagicMock(spec=VaultGraph)

        mock_scanner.scan.return_value = mock_vault_index
        mock_graph_builder.build_full_graph.return_value = mock_full_graph

        use_case = ShowNoteUseCase(
            scanner=mock_scanner,
            graph_builder=mock_graph_builder,
        )

        with patch("vault_net.application.use_cases.show_note.VaultRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.resolve_to_slug.return_value = "test-slug"

            mock_note = MagicMock(spec=VaultNote)
            mock_note.slug = "test-slug"
            mock_note.file_path = "test/path.md"
            mock_note.file_hash = "abc123"
            mock_note.status = "active"
            mock_note.error = None
            mock_note.frontmatter = {}
            mock_note.stats = MagicMock()
            mock_note.stats.file_size = 100
            mock_note.stats.modified_time = "2024-01-01"
            mock_note.stats.access_time = "2024-01-02"
            mock_note.to_file.return_value = VaultFile(slug="test-slug", file_path="test/path.md")
            mock_registry.get_file.return_value = mock_note

            MockRegistry.return_value = mock_registry

            mock_full_graph.digraph.successors.return_value = ["other-slug"]
            mock_full_graph.digraph.predecessors.return_value = ["another-slug"]

            result = use_case.execute(
                vault_root=tmp_path,
                note_input="test-slug",
                extra_exclude_dir=("excluded",),
                no_default_excludes=True,
            )

        mock_scanner.scan.assert_called_once_with(
            tmp_path,
            extra_exclude_dir=("excluded",),
            no_default_excludes=True,
        )
        mock_graph_builder.build_full_graph.assert_called_once_with(mock_vault_index)

        assert isinstance(result, NoteShow)
        assert result.note.slug == "test-slug"

    def test_execute_extracts_forward_and_backward_links(self, tmp_path: Path) -> None:
        """Verify forward and backward links are extracted from graph."""
        mock_scanner = MagicMock()
        mock_graph_builder = MagicMock()

        mock_vault_index = MagicMock(spec=VaultIndex)
        mock_full_graph = MagicMock(spec=VaultGraph)
        mock_scanner.scan.return_value = mock_vault_index
        mock_graph_builder.build_full_graph.return_value = mock_full_graph

        use_case = ShowNoteUseCase(
            scanner=mock_scanner,
            graph_builder=mock_graph_builder,
        )

        with patch("vault_net.application.use_cases.show_note.VaultRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.resolve_to_slug.return_value = "source-slug"

            source_note = MagicMock(spec=VaultNote)
            source_note.slug = "source-slug"
            source_note.file_path = "source.md"
            source_note.file_hash = "hash1"
            source_note.status = "active"
            source_note.error = None
            source_note.frontmatter = None
            source_note.stats = MagicMock()
            source_note.to_file.return_value = VaultFile(slug="source-slug", file_path="source.md")

            forward_note = MagicMock(spec=VaultNote)
            forward_note.slug = "forward-slug"
            forward_note.file_path = "forward.md"
            forward_note.to_file.return_value = VaultFile(
                slug="forward-slug", file_path="forward.md"
            )

            backward_note = MagicMock(spec=VaultNote)
            backward_note.slug = "backward-slug"
            backward_note.file_path = "backward.md"
            backward_note.to_file.return_value = VaultFile(
                slug="backward-slug", file_path="backward.md"
            )

            def get_file_side_effect(slug: str) -> MagicMock | None:
                if slug == "source-slug":
                    return source_note
                if slug == "forward-slug":
                    return forward_note
                if slug == "backward-slug":
                    return backward_note
                return None

            mock_registry.get_file.side_effect = get_file_side_effect
            MockRegistry.return_value = mock_registry

            mock_full_graph.digraph.successors.return_value = ["forward-slug"]
            mock_full_graph.digraph.predecessors.return_value = ["backward-slug"]

            result = use_case.execute(
                vault_root=tmp_path,
                note_input="source-slug",
            )

        assert isinstance(result, NoteShow)
        assert result.note.slug == "source-slug"
        assert len(result.forward_links) == 1
        assert result.forward_links[0].slug == "forward-slug"
        assert len(result.backward_links) == 1
        assert result.backward_links[0].slug == "backward-slug"

    def test_execute_passes_unknown_slug_error_upstream(self, tmp_path: Path) -> None:
        """KeyError when slug cannot be resolved is propagated."""
        mock_scanner = MagicMock()
        mock_graph_builder = MagicMock()

        mock_vault_index = MagicMock(spec=VaultIndex)
        mock_scanner.scan.return_value = mock_vault_index

        use_case = ShowNoteUseCase(
            scanner=mock_scanner,
            graph_builder=mock_graph_builder,
        )

        with patch("vault_net.application.use_cases.show_note.VaultRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.resolve_to_slug.return_value = None
            MockRegistry.return_value = mock_registry

            with pytest.raises(KeyError, match="unknown-slug"):
                use_case.execute(tmp_path, "unknown-slug")
