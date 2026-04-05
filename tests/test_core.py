"""Initialization tests for link-tracer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from link_tracer import __version__
from link_tracer.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def test_package_exposes_version() -> None:
    """Expose a non-empty package version string."""
    assert __version__


def test_cli_prints_stub_payload(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Print placeholder JSON from the initialized CLI."""
    note = tmp_path / "note.md"
    note.write_text("# Demo\n", encoding="utf-8")

    exit_code = main([str(note), "--vault", str(tmp_path)])

    captured = capsys.readouterr().out
    payload = json.loads(captured)

    assert exit_code == 0
    assert payload["note_path"] == str(note)
    assert payload["vault_root"] == str(tmp_path)
    assert payload["nodes"] == []
    assert payload["edges"] == []
    assert payload["errors"][0]["code"] == "not_implemented"


def test_cli_help_exits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    """Show help text and exit with argparse success code."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "Trace Obsidian note links" in output
