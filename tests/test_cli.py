"""Tests for vault-net CLI and vault directory resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.fixtures import create_sample_vault
from vault_net import __version__
from vault_net.cli import main


def test_package_exposes_version() -> None:
    """Expose a non-empty package version string."""
    assert __version__


def test_cli_help_exits_cleanly() -> None:
    """Show help text and exit with success code."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Trace Obsidian note links" in result.output


def test_note_graph_uses_slug_argument(tmp_path: Path) -> None:
    """note-graph resolves by slug instead of file path."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("[[about]]", encoding="utf-8")
    (vault / "about.md").write_text("", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", "home.md", "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)
    assert payload["metadata"]["edge_count"] == 1
    assert payload["edges"] == [
        [{"slug": "home.md", "file_path": "home.md"}, {"slug": "about.md", "file_path": "about.md"}]
    ]


def test_note_graph_unknown_slug_returns_usage_error(tmp_path: Path) -> None:
    """Unknown slug returns a CLI usage error."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", "missing.md", "--vault-root", str(vault)])

    assert result.exit_code != 0
    assert "Unknown slug" in result.output


def test_note_graph_format_adjacency_list(tmp_path: Path) -> None:
    """note-graph supports adjacency_list format."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("[[about]]", encoding="utf-8")
    (vault / "about.md").write_text("", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["note-graph", "home.md", "--vault-root", str(vault), "--format", "adjacency_list"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["home.md"] == [{"slug": "about.md", "file_path": "about.md"}]
    assert payload["about.md"] == []


def test_note_graph_format_layered(tmp_path: Path) -> None:
    """note-graph supports layered format."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("[[about]]", encoding="utf-8")
    (vault / "about.md").write_text("", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["note-graph", "home.md", "--vault-root", str(vault), "--format", "layered"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["source_note"] == "home.md"
    assert payload["total_files"] == 2
    assert payload["layers"][0] == {"depth": 0, "note": "home.md"}


def test_edges_command_default_edge_list(tmp_path: Path) -> None:
    """edges defaults to edge_list output."""
    create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"

    runner = CliRunner()
    result = runner.invoke(main, ["edges", "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)
    assert payload["metadata"]["edge_count"] >= 1
    assert payload["edges"]
    assert "slug" in payload["edges"][0][0]


def test_edges_command_format_adjacency_list(tmp_path: Path) -> None:
    """edges supports adjacency_list format."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("[[about]]", encoding="utf-8")
    (vault / "about.md").write_text("", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["edges", "--vault-root", str(vault), "--format", "adjacency_list"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["home.md"] == [{"slug": "about.md", "file_path": "about.md"}]
    assert payload["about.md"] == []


def test_cli_errors_without_vault_root() -> None:
    """Exit with error when no vault directory is provided."""
    runner = CliRunner()
    result = runner.invoke(main, ["edges"])

    assert result.exit_code != 0
    assert "No vault root directory provided" in result.output


def test_note_graph_output_writes_json_file(tmp_path: Path) -> None:
    """-o/--output writes note JSON payload to a file."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("", encoding="utf-8")
    output = tmp_path / "note-output.json"

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["note-graph", "home.md", "--vault-root", str(vault), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert result.output == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["vault_root"] == str(vault)
    assert payload["metadata"]["edge_count"] == 0
    assert payload["edges"] == []


def test_cli_uses_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAULT_ROOT env var works when --vault-root is missing."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "home.md").write_text("", encoding="utf-8")
    monkeypatch.setenv("VAULT_ROOT", str(vault))

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", "home.md"], catch_exceptions=False)

    assert result.exit_code == 0
