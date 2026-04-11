"""Slug-related business rules."""

from __future__ import annotations

from vault_net.consts import SLUG_LENGTH


def generate_slug(filename: str, slug_counts: dict[str, int]) -> str:
    """Generate a unique slug for a filename with max `SLUG_LENGTH` chars."""
    base_slug = filename[:SLUG_LENGTH].replace(" ", "-")
    slug = base_slug
    count = slug_counts.get(base_slug, 0)
    while slug in slug_counts:
        suffix = f"_{count}"
        shortened_len = max(1, SLUG_LENGTH - len(suffix))
        shortened_base = base_slug[:shortened_len]
        slug = f"{shortened_base}{suffix}"
        count += 1
    slug_counts[slug] = 0
    slug_counts[base_slug] = count
    slug = slug.ljust(SLUG_LENGTH, "-")
    return slug
