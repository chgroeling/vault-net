"""Integration test utility with sample Obsidian note files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SAMPLE_NOTES: dict[str, str] = {
    "home.md": """\
---
title: Home
tags: [index]
---
# Home

Welcome to the vault. See [[About]] for details.
Check out [Markdown Link](https://example.com) for external reference.
Visit https://obsidian.md for more info.
""",
    "about.md": """\
---
title: About
tags: [info]
---
# About

This vault is for testing. Related: [[Projects]] and [[Tasks]].
Embed: ![[Diagram]]
""",
    "projects.md": """\
---
title: Projects
tags: [work]
---
# Projects

Active: [[Project Alpha|Alpha]]
Reference: [Docs](https://docs.example.com)
See also [[Tasks#Priority]] and [[Notes^block123]].
""",
    "tasks.md": """\
---
title: Tasks
tags: [work, todo]
---
# Tasks

## Priority
- Finish [[Project Alpha]]
- Review [[Meeting Notes]]

## Backlog
- Update [[Home]]
""",
    "project_alpha.md": """\
---
title: Project Alpha
tags: [work, active]
---
# Project Alpha

Status: in progress.
Links: [[Projects]], [[Tasks]], [Report](reports/q1.pdf)
""",
    "meeting_notes.md": """\
---
title: Meeting Notes
date: 2025-01-15
---
# Meeting Notes

Attendees discussed [[Project Alpha]].
Action items in [[Tasks]].
Calendar: https://calendar.google.com
""",
    "notes.md": """\
---
title: Random Notes
---
# Random Notes

Idea from [[About]].
See [[Home#Welcome]] for context.
Block ref: [[tasks^block456]]
External: ftp://files.example.com/data
""",
    "diagram.md": """\
---
title: Diagram
---
# Diagram

![[architecture.png]]

Related notes: [[Projects]], [[About]].
""",
    "reading_list.md": """\
---
title: Reading List
tags: [personal]
---
# Reading List

- [Article](https://blog.example.com/post)
- [[Notes]] has good summaries
- Check [[Home]] for vault structure
""",
    "archive.md": """\
---
title: Archive
tags: [archive]
---
# Archive

Old project: [[Project Alpha|Alpha (archived)]]
See [old docs](https://old.example.com)
No internal links here.
""",
}

TEST_VAULT_NOTES: dict[str, str] = {
    "home.md": """\
---
title: Home
---
# Home

Unqualified link: [[about]].
Qualified link: [[teams/about]].
""",
    "docs/about.md": """\
---
title: Docs About
---
# Docs About
""",
    "teams/about.md": """\
---
title: Teams About
---
# Teams About
""",
}


def create_sample_vault(tmp_path: Path) -> dict[str, Path]:
    """Create all 10 sample notes in a temp directory and return paths."""
    vault = tmp_path / "sample_vault"
    vault.mkdir()
    paths: dict[str, Path] = {}
    for name, content in SAMPLE_NOTES.items():
        note_path = vault / name
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(content, encoding="utf-8")
        paths[name] = note_path
    return paths


def create_test_vault(tmp_path: Path) -> dict[str, Path]:
    """Create a vault with duplicate filenames in nested directories."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    paths: dict[str, Path] = {}
    for name, content in TEST_VAULT_NOTES.items():
        note_path = vault / name
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(content, encoding="utf-8")
        paths[name] = note_path
    return paths


# ---------------------------------------------------------------------------
# Fake matterify dataclasses for unit tests
# ---------------------------------------------------------------------------


@dataclass
class FakeFileStats:
    file_size: int = 100
    modified_time: float = 1700000000.0
    access_time: float = 1700000000.0


@dataclass
class FakeFileEntry:
    file_path: str = "note.md"
    frontmatter: dict = field(default_factory=dict)
    status: str = "ok"
    error: str | None = None
    stats: FakeFileStats | None = field(default_factory=FakeFileStats)
    file_hash: str | None = None


@dataclass
class FakeScanMetadata:
    source_directory: Path = field(default_factory=lambda: Path("/tmp/vault"))  # noqa: S108


@dataclass
class FakeAggregatedResult:
    metadata: FakeScanMetadata = field(default_factory=FakeScanMetadata)
    files: list[FakeFileEntry] = field(default_factory=list)

