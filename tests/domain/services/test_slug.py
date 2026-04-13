"""Domain service tests for slug generation."""

from __future__ import annotations

from vault_net.domain.services.slug_service import generate_slug


def test_generate_slug_simple_filename() -> None:
    """Simple filename generates slug without modification."""
    slug_counts: dict[str, int] = {}
    result = generate_slug("note", slug_counts)
    assert result == "NOTE____"
    assert len(result) == 8


def test_generate_slug_truncates_long_filename() -> None:
    """Filename longer than SLUG_LENGTH is truncated."""
    slug_counts: dict[str, int] = {}
    result = generate_slug("verylongfilename", slug_counts)
    assert len(result) <= 8
    assert result == "VERYLONG"


def test_generate_slug_replaces_spaces_with_underscores() -> None:
    """Spaces in filename are replaced with underscores."""
    slug_counts: dict[str, int] = {}
    result = generate_slug("my note", slug_counts)
    assert result == "MY_NOTE_"
    assert len(result) == 8


def test_generate_slug_truncates_and_replaces_spaces() -> None:
    """Long filename with spaces is truncated and spaces are replaced."""
    slug_counts: dict[str, int] = {}
    result = generate_slug("my long note name", slug_counts)
    assert " " not in result
    assert result.startswith("MY_")
    assert len(result) == 8


def test_generate_slug_first_duplicate_gets_suffix() -> None:
    """First collision appends 0 suffix."""
    slug_counts: dict[str, int] = {}
    first = generate_slug("note", slug_counts)
    second = generate_slug("note", slug_counts)
    assert first == "NOTE____"
    assert second == "NOTE0___"
    assert len(first) == 8
    assert len(second) == 8


def test_generate_slug_second_duplicate_gets_incremented_suffix() -> None:
    """Second collision increments suffix to 1."""
    slug_counts: dict[str, int] = {}
    generate_slug("note", slug_counts)
    third = generate_slug("note", slug_counts)
    assert third == "NOTE0___"
    assert len(third) == 8


def test_generate_slug_different_filenames_independent() -> None:
    """Different filenames do not collide."""
    slug_counts: dict[str, int] = {}
    note_slug = generate_slug("note", slug_counts)
    other_slug = generate_slug("other", slug_counts)
    assert note_slug == "NOTE____"
    assert other_slug == "OTHER___"
    assert len(note_slug) == 8
    assert len(other_slug) == 8


def test_generate_slug_collision_shortens_base_when_needed() -> None:
    """When suffix would exceed SLUG_LENGTH, base is shortened."""
    slug_counts: dict[str, int] = {}
    generate_slug("longname", slug_counts)
    result = generate_slug("longname", slug_counts)
    assert len(result) == 8
    assert result.startswith("LONGN")


def test_generate_slug_updates_counts_for_tracking() -> None:
    """slug_counts is updated to track collisions."""
    slug_counts: dict[str, int] = {}
    generate_slug("note", slug_counts)
    generate_slug("note", slug_counts)
    assert slug_counts["NOTE"] == 1
    assert "NOTE" in slug_counts


def test_generate_slug_handles_reserved_suffix_collision() -> None:
    """Collision with existing _N suffix skips to next available."""
    slug_counts: dict[str, int] = {}
    result1 = generate_slug("longname", slug_counts)
    result2 = generate_slug("longname", slug_counts)
    result3 = generate_slug("longname_0", slug_counts)
    assert result1 == "LONGNAME"
    assert result2 == "LONGNAM0"
    assert result3 == "LONGNAM1"
    assert len(result1) == 8
    assert len(result2) == 8
    assert len(result3) == 8


def test_generate_slug_respects_max_length() -> None:
    """All generated slugs are exactly SLUG_LENGTH."""
    slug_counts: dict[str, int] = {}
    result = generate_slug("longfilename", slug_counts)
    assert len(result) == 8


def test_generate_slug_many_collisions_remain_unique() -> None:
    """Slug generation handles many collisions and produces unique slugs."""
    slug_counts: dict[str, int] = {}
    slugs = [generate_slug("filename", slug_counts) for _ in range(12)]
    assert len(slugs) == len(set(slugs)), "All slugs must be unique"
    for slug in slugs:
        assert len(slug) == 8


def test_generate_slug_collision_at_length_boundary() -> None:
    """Collision near max length produces correct shortened base + suffix."""
    slug_counts: dict[str, int] = {}
    slug1 = generate_slug("abcdefgh", slug_counts)
    slug2 = generate_slug("abcdefgh", slug_counts)
    assert len(slug1) == 8
    assert len(slug2) == 8
    assert slug1 == "ABCDEFGH"
    assert slug2 == "ABCDEFG0"


def test_generate_slug_short_filename_pads_to_8() -> None:
    """Short filenames are padded with underscores to reach exactly 8 chars."""
    slug_counts: dict[str, int] = {}
    assert generate_slug("ab.md", slug_counts) == "AB_MD___"
    assert generate_slug("a.md", slug_counts) == "A_MD____"
    assert generate_slug("abc.md", slug_counts) == "ABC_MD__"
