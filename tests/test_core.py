"""Tests for link-tracer CLI and vault directory resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from link_tracer import __version__
from link_tracer.cli import main


def test_package_exposes_version() -> None:
    """Expose a non-empty package version string."""
    assert __version__


def test_cli_prints_stub_payload(tmp_path: Path) -> None:
    """Print placeholder JSON from the initialized CLI."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["note_path"] == str(note)
    assert payload["vault_root"] == str(tmp_path)
    assert "metadata" in payload
    assert "files" in payload


def test_cli_help_exits_cleanly() -> None:
    """Show help text and exit with success code."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Trace Obsidian note links" in result.output


def test_cli_uses_vault_dir_option(tmp_path: Path) -> None:
    """--vault-dir option overrides all other sources."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    vault = tmp_path / "vault"
    vault.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_uses_dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """.vault file overrides VAULT_DIR env var."""
    monkeypatch.setenv("VAULT_DIR", str(tmp_path / "wrong"))

    project = tmp_path / "project"
    project.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    note = project / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    (project / ".vault").write_text(f"VAULT_DIR={vault}\n", encoding="utf-8")

    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(main, [str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_dotenv_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """.vault with relative path resolves from .vault file's directory."""
    project = tmp_path / "project"
    project.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    note = project / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    (project / ".vault").write_text("VAULT_DIR=../vault\n", encoding="utf-8")

    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(main, [str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_uses_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAULT_DIR env var works when no .vault or --vault-dir."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_DIR", str(vault))

    runner = CliRunner()
    result = runner.invoke(main, [str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_env_var_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAULT_DIR with relative path resolves from cwd."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_DIR", "vault")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_dotenv_without_vault_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """.vault without VAULT_DIR falls through to env var."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    (tmp_path / ".vault").write_text("OTHER_VAR=some_value\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_DIR", str(vault))

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_errors_without_vault_dir(tmp_path: Path) -> None:
    """Exit with error when no vault directory is provided."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note)])

    assert result.exit_code != 0
    assert "No vault directory provided" in result.output


def test_cli_errors_on_nonexistent_vault_dir(tmp_path: Path) -> None:
    """Exit with error when vault directory does not exist."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    nonexistent = tmp_path / "nonexistent"

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(nonexistent)])

    assert result.exit_code != 0
    assert "Vault directory does not exist" in result.output
    assert str(nonexistent) in result.output


def test_cli_pretty_print(tmp_path: Path) -> None:
    """--pretty flag formats JSON with indentation."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(tmp_path), "--pretty"])

    assert result.exit_code == 0
    assert "  " in result.output
    payload = json.loads(result.output)
    assert payload["note_path"] == str(note)


def test_cli_scans_vault_with_frontmatter(tmp_path: Path) -> None:
    """Integration test: scan vault and return frontmatter data for markdown files."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note_with_fm = vault / "with_fm.md"
    note_with_fm.write_text("---\ntitle: Test Note\ntags: [test]\n---\n# Hello\n", encoding="utf-8")
    note_without_fm = vault / "without_fm.md"
    note_without_fm.write_text("# No Frontmatter\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note_with_fm), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)
    assert payload["metadata"]["total_files"] == 2
    assert payload["metadata"]["files_with_frontmatter"] == 1
    assert payload["metadata"]["files_without_frontmatter"] == 1
    assert payload["metadata"]["errors"] == 0
    files = {f["file_path"].split("/")[-1]: f for f in payload["files"]}
    assert files["with_fm.md"]["frontmatter"] == {"title": "Test Note", "tags": ["test"]}
    assert files["with_fm.md"]["status"] == "ok"
    assert files["without_fm.md"]["frontmatter"] is None
    assert files["without_fm.md"]["status"] == "illegal"
    assert files["without_fm.md"]["error"] == "no_frontmatter"
