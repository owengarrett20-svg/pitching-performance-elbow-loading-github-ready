"""Small, allowlisted locations for shareable public research views."""

from __future__ import annotations

from collections.abc import Iterable

PAGES = (
    "Start here",
    "Explore pitches",
    "Watch motion",
    "Study results",
    "Methods & collaboration",
)
PAGE_SLUGS = dict(zip(PAGES, ("start", "explore", "motion", "study", "methods")))
SLUG_PAGES = {slug: page for page, slug in PAGE_SLUGS.items()}


def resolve_location(
    page_slug: str | None, pitch_id: str | None, valid_pitch_ids: Iterable[str]
) -> tuple[str, str | None]:
    """Resolve untrusted URL values without using them as paths or source data."""
    page = SLUG_PAGES.get(page_slug, PAGES[0])
    valid = {str(value) for value in valid_pitch_ids}
    pitch = pitch_id if isinstance(pitch_id, str) and pitch_id in valid else None
    return page, pitch
