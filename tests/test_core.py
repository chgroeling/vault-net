"""Tests for link-tracer CLI and vault directory resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from link_tracer import __version__
from link_tracer.cli import main
from tests.test_utils import create_sample_vault


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


def test_trace_filters_files_to_matched_links(tmp_path: Path) -> None:
    """Filtered output contains only files matched by links in the traced note."""
    paths = create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"

    runner = CliRunner()
    result = runner.invoke(main, [str(paths["home.md"]), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["metadata"]["total_files"] == 1
    assert payload["metadata"]["files_with_frontmatter"] == 1
    assert payload["metadata"]["files_without_frontmatter"] == 0
    assert payload["metadata"]["errors"] == 0
    assert len(payload["files"]) == 1
    assert payload["files"][0]["file_path"].endswith("about.md")
    assert payload["files"][0]["frontmatter"] == {"title": "About", "tags": ["info"]}
    assert payload["files"][0]["status"] == "ok"
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.md")


def test_trace_filters_multiple_matched_files(tmp_path: Path) -> None:
    """Filtered output contains all files matched by links in the traced note."""
    paths = create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"

    runner = CliRunner()
    result = runner.invoke(main, [str(paths["about.md"]), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["metadata"]["total_files"] == 3
    assert payload["metadata"]["files_with_frontmatter"] == 3
    assert payload["metadata"]["files_without_frontmatter"] == 0
    assert payload["metadata"]["errors"] == 0
    assert len(payload["files"]) == 3
    file_names = {f["file_path"].split("/")[-1] for f in payload["files"]}
    assert file_names == {"projects.md", "tasks.md", "diagram.md"}
    assert len(payload["matched_links"]) == 3


def test_trace_links_matches_link_without_extension(tmp_path: Path) -> None:
    """Links without extensions match files with .md extension."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "matched_links" in payload
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.md")


def test_trace_links_matches_link_with_uppercase_extension(tmp_path: Path) -> None:
    """Links without extensions match files with .MD extension."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.MD").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.MD")


def test_trace_links_matches_link_with_markdown_extension(tmp_path: Path) -> None:
    """Links without extensions match files with .markdown extension."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.markdown").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.markdown")


def test_trace_links_matches_link_with_extension(tmp_path: Path) -> None:
    """Links with explicit extensions match directly."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about.md]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.md")


def test_trace_links_matches_heading_reference(tmp_path: Path) -> None:
    """Links with heading references (#) are resolved to files."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about#Section]].\n", encoding="utf-8")
    (vault / "about.md").write_text(
        "---\ntitle: About\n---\n# About\n\n## Section\n", encoding="utf-8"
    )

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.md")


def test_trace_links_matches_block_reference(tmp_path: Path) -> None:
    """Links with block references (^) are resolved to files."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about^block123]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [str(note), "--vault-dir", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload["matched_links"]) == 1
    assert payload["matched_links"][0].endswith("about.md")
