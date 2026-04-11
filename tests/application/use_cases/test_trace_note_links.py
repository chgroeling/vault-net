"""Tests for TraceNoteLinksUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vault_net.application.use_cases.trace_note_links import TraceNoteLinksUseCase
from vault_net.domain.models import NoteLinkTrace, VaultGraph, VaultIndex


class TestTraceNoteLinksUseCase:
    """Verify TraceNoteLinksUseCase orchestration."""

    def test_execute_orchestrates_scan_then_build_full_then_neighborhood(
        self, tmp_path: Path
    ) -> None:
        """Verify scan -> build_full_graph -> build_neighborhood_graph call order."""
        mock_scanner = MagicMock()
        mock_graph_builder = MagicMock()

        mock_vault_index = MagicMock(spec=VaultIndex)
        mock_full_graph = MagicMock(spec=VaultGraph)
        mock_neighborhood_graph = MagicMock(spec=VaultGraph)

        mock_scanner.scan.return_value = mock_vault_index
        mock_graph_builder.build_full_graph.return_value = mock_full_graph
        mock_graph_builder.build_neighborhood_graph.return_value = mock_neighborhood_graph

        use_case = TraceNoteLinksUseCase(
            scanner=mock_scanner,
            graph_builder=mock_graph_builder,
        )

        with patch(
            "vault_net.application.use_cases.trace_note_links.VaultRegistry"
        ) as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.resolve_to_slug.return_value = "test-slug"
            MockRegistry.return_value = mock_registry

            result = use_case.execute(
                vault_root=tmp_path,
                note_input="test-slug",
                depth=2,
                extra_exclude_dir=("excluded",),
                no_default_excludes=True,
            )

        mock_scanner.scan.assert_called_once_with(
            tmp_path,
            extra_exclude_dir=("excluded",),
            no_default_excludes=True,
        )
        mock_graph_builder.build_full_graph.assert_called_once_with(mock_vault_index)
        mock_graph_builder.build_neighborhood_graph.assert_called_once_with(
            "test-slug", mock_full_graph, depth=2
        )

        assert isinstance(result, NoteLinkTrace)
        assert result.source_slug == "test-slug"
        assert result.vault_index is mock_vault_index
        assert result.neighborhood_graph is mock_neighborhood_graph

    def test_execute_passes_unknown_slug_error_upstream(self, tmp_path: Path) -> None:
        """KeyError from build_neighborhood_graph is propagated."""
        mock_scanner = MagicMock()
        mock_graph_builder = MagicMock()

        mock_full_graph = MagicMock(spec=VaultGraph)
        mock_graph_builder.build_full_graph.return_value = mock_full_graph
        mock_graph_builder.build_neighborhood_graph.side_effect = KeyError("unknown-slug")

        use_case = TraceNoteLinksUseCase(
            scanner=mock_scanner,
            graph_builder=mock_graph_builder,
        )

        with pytest.raises(KeyError, match="unknown-slug"):
            use_case.execute(tmp_path, "unknown-slug")
