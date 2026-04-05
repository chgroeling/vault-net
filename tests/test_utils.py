"""Integration test utility with sample Obsidian note files."""

from __future__ import annotations

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


def create_sample_vault(tmp_path: Path) -> dict[str, Path]:
    """Create all 10 sample notes in a temp directory and return paths."""
    vault = tmp_path / "sample_vault"
    vault.mkdir()
    paths: dict[str, Path] = {}
    for name, content in SAMPLE_NOTES.items():
        note_path = vault / name
        note_path.write_text(content, encoding="utf-8")
        paths[name] = note_path
    return paths
