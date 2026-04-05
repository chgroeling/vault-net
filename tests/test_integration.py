"""Integration test: extract links from sample notes using obsilink."""

from __future__ import annotations

from pathlib import Path

from obsilink import extract_links

from tests.test_utils import create_sample_vault


def test_extract_internal_links_from_sample_note(tmp_path: Path) -> None:
    """Extract non-URL links from a sample note and print to console."""
    vault_paths = create_sample_vault(tmp_path)
    note_path = vault_paths["projects.md"]

    content = note_path.read_text(encoding="utf-8")
    links = extract_links(content)

    internal_links = [link for link in links if link.is_file]

    print(f"\nExtracted {len(internal_links)} internal links from {note_path.name}:")
    for link in internal_links:
        print(f"  Type: {link.type.value:20s} | Target: {link.target}")

    assert len(internal_links) == 3
    assert internal_links[0].target == "Project Alpha"
    assert internal_links[0].alias == "Alpha"
    assert internal_links[1].target == "Tasks"
    assert internal_links[1].heading == "Priority"
    assert internal_links[2].target == "Notes"
    assert internal_links[2].blockid == "block123"
