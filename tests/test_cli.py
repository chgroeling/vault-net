"""Tests for link-tracer CLI and vault directory resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from link_tracer import __version__
from link_tracer.cli import main
from tests.fixtures import create_sample_vault, create_test_vault


def test_package_exposes_version() -> None:
    """Expose a non-empty package version string."""
    assert __version__


def test_cli_prints_stub_payload(tmp_path: Path) -> None:
    """Print placeholder JSON from the initialized CLI."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(tmp_path)
    assert "metadata" in payload
    assert "edges" in payload


def test_cli_help_exits_cleanly() -> None:
    """Show help text and exit with success code."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Trace Obsidian note links" in result.output


def test_cli_uses_vault_root_option(tmp_path: Path) -> None:
    """--vault-root option overrides all other sources."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    vault = tmp_path / "vault"
    vault.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_uses_dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """.vault file overrides VAULT_ROOT env var."""
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path / "wrong"))

    project = tmp_path / "project"
    project.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    note = project / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    (project / ".vault").write_text(f"VAULT_ROOT={vault}\n", encoding="utf-8")

    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note)], catch_exceptions=False)

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
    (project / ".vault").write_text("VAULT_ROOT=../vault\n", encoding="utf-8")

    monkeypatch.chdir(project)
    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_uses_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAULT_ROOT env var works when no .vault or --vault-root."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_ROOT", str(vault))

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_env_var_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """VAULT_ROOT with relative path resolves from cwd."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_ROOT", "vault")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_dotenv_without_vault_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """.vault without VAULT_ROOT falls through to env var."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    (tmp_path / ".vault").write_text("OTHER_VAR=some_value\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_ROOT", str(vault))

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note)], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)


def test_cli_errors_without_vault_root(tmp_path: Path) -> None:
    """Exit with error when no vault directory is provided."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note)])

    assert result.exit_code != 0
    assert "No vault root directory provided" in result.output


def test_cli_errors_on_nonexistent_vault_root(tmp_path: Path) -> None:
    """Exit with error when vault root directory does not exist."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    nonexistent = tmp_path / "nonexistent"

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(nonexistent)])

    assert result.exit_code != 0
    assert "Vault root directory does not exist" in result.output
    assert str(nonexistent) in result.output


def test_cli_pretty_print(tmp_path: Path) -> None:
    """JSON output is always pretty-printed with indentation."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "  " in result.output


def test_trace_filters_files_to_matched_links(tmp_path: Path) -> None:
    """Filtered output contains only files matched by links in the traced note."""
    paths = create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(paths["home.md"]), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["metadata"]["total_files"] == 5
    assert payload["metadata"]["files_with_frontmatter"] == 5
    assert payload["metadata"]["files_without_frontmatter"] == 0
    assert payload["metadata"]["errors"] == 0
    # Forward edge
    assert payload["edges"]["home.md"][0]["target_note"] == "about.md"
    assert payload["edges"]["home.md"][0]["resolved"] is True
    assert payload["edges"]["home.md"][0]["link"]["target"].lower() == "about"
    # Backlink edges into home
    assert set(payload["edges"]) == {"home.md", "tasks.md", "notes.md", "reading_list.md"}


def test_trace_filters_multiple_matched_files(tmp_path: Path) -> None:
    """Filtered output contains all files matched by links in the traced note."""
    paths = create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(paths["about.md"]), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["metadata"]["total_files"] == 6
    assert payload["metadata"]["files_with_frontmatter"] == 6
    assert payload["metadata"]["files_without_frontmatter"] == 0
    assert payload["metadata"]["errors"] == 0
    # Forward edges from about
    assert [edge["target_note"] for edge in payload["edges"]["about.md"]] == [
        "projects.md",
        "tasks.md",
        "diagram.md",
    ]
    # Backlink edges into about
    assert set(payload["edges"]) == {"about.md", "home.md", "notes.md", "diagram.md"}


def test_trace_links_matches_link_without_extension(tmp_path: Path) -> None:
    """Links without extensions match files with .md extension."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "edges" in payload
    assert set(payload["edges"]) == {"home.md"}
    assert payload["edges"]["home.md"][0]["target_note"] == "about.md"


def test_trace_links_matches_link_with_uppercase_extension(tmp_path: Path) -> None:
    """Links without extensions match files with .MD extension."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.MD").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload["edges"]) == {"home.md"}
    assert payload["edges"]["home.md"][0]["target_note"] == "about.MD"


def test_trace_links_matches_link_with_markdown_extension(tmp_path: Path) -> None:
    """Links without extensions match files with .markdown extension."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.markdown").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload["edges"]) == {"home.md"}
    assert payload["edges"]["home.md"][0]["target_note"] == "about.markdown"


def test_trace_links_matches_link_with_extension(tmp_path: Path) -> None:
    """Links with explicit extensions match directly."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about.md]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload["edges"]) == {"home.md"}
    assert payload["edges"]["home.md"][0]["target_note"] == "about.md"


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
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload["edges"]) == {"home.md"}
    assert payload["edges"]["home.md"][0]["target_note"] == "about.md"


def test_trace_links_matches_block_reference(tmp_path: Path) -> None:
    """Links with block references (^) are resolved to files."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about^block123]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload["edges"]) == {"home.md"}
    assert payload["edges"]["home.md"][0]["target_note"] == "about.md"


def test_trace_links_uses_path_component_for_duplicate_names(tmp_path: Path) -> None:
    """Path-qualified links resolve duplicate filenames in different folders."""
    paths = create_test_vault(tmp_path)
    vault = tmp_path / "test_vault"

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(paths["home.md"]), "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload["edges"]) == {"home.md"}
    assert [edge["target_note"] for edge in payload["edges"]["home.md"]] == [
        "docs/about.md",
        "teams/about.md",
    ]


def test_note_graph_default_format_returns_edges_key(tmp_path: Path) -> None:
    """Omitting --format produces the edges representation by default."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["note-graph", str(note), "--vault-root", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "edges" in payload
    assert "layers" not in payload


def test_note_graph_format_edges_returns_edges_key(tmp_path: Path) -> None:
    """--format edges explicitly produces the edge-dict representation."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main, ["note-graph", str(note), "--vault-root", str(tmp_path), "--format", "edges"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "edges" in payload
    assert "layers" not in payload


def test_note_graph_format_layered_returns_layers_key(tmp_path: Path) -> None:
    """--format layered produces a layers list and no edges key."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main, ["note-graph", str(note), "--vault-root", str(tmp_path), "--format", "layered"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "layers" in payload
    assert "edges" not in payload
    assert isinstance(payload["layers"], list)


def test_note_graph_format_layered_source_at_depth_zero(tmp_path: Path) -> None:
    """--format layered places source note at depth 0."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main, ["note-graph", str(note), "--vault-root", str(vault), "--format", "layered"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    depth_zero = [e for e in payload["layers"] if e["depth"] == 0]
    assert len(depth_zero) == 1
    assert depth_zero[0]["note"] == "home.md"


def test_note_graph_format_layered_linked_note_at_depth_one(tmp_path: Path) -> None:
    """--format layered places directly linked notes at depth 1."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main, ["note-graph", str(note), "--vault-root", str(vault), "--format", "layered"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    depth_one = [e for e in payload["layers"] if e["depth"] == 1]
    assert any(e["note"] == "about.md" for e in depth_one)


def test_note_graph_format_layered_depth_zero_returns_source_only(tmp_path: Path) -> None:
    """--format layered with --depth 0 returns only the source note at depth 0."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "home.md"
    note.write_text("---\ntitle: Home\n---\n# Home\n\nSee [[about]].\n", encoding="utf-8")
    (vault / "about.md").write_text("---\ntitle: About\n---\n# About\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["note-graph", str(note), "--vault-root", str(vault), "--format", "layered", "--depth", "0"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["layers"] == [{"depth": 0, "note": "home.md"}]


def test_vault_command_outputs_edges_for_multiple_notes(tmp_path: Path) -> None:
    """Vault subcommand resolves links across every note in the vault."""
    create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"

    runner = CliRunner()
    result = runner.invoke(main, ["vault-graph", "--vault-root", str(vault)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["vault_root"] == str(vault)
    assert payload["metadata"]["total_files"] == 10
    assert "home.md" in payload["edges"]
    assert "about.md" in payload["edges"]


def test_vault_command_requires_vault_root() -> None:
    """Vault subcommand errors when no vault root can be resolved."""
    runner = CliRunner()
    result = runner.invoke(main, ["vault-graph"], env={})

    assert result.exit_code != 0
    assert "No vault root directory provided" in result.output


def test_note_command_output_writes_json_file(tmp_path: Path) -> None:
    """-o/--output writes note JSON payload to a file."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")
    output = tmp_path / "note-output.json"

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["note-graph", str(note), "--vault-root", str(tmp_path), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert result.output == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["vault_root"] == str(tmp_path)


def test_vault_command_output_writes_json_file(tmp_path: Path) -> None:
    """-o/--output writes vault JSON payload to a file."""
    create_sample_vault(tmp_path)
    vault = tmp_path / "sample_vault"
    output = tmp_path / "vault-output.json"

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["vault-graph", "--vault-root", str(vault), "-o", str(output)],
    )

    assert result.exit_code == 0
    assert result.output == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["vault_root"] == str(vault)
    assert payload["metadata"]["total_files"] == 10
