"""Public links can select recorded observations, never arbitrary source paths."""

import pytest

from pitching.site_navigation import PAGE_SLUGS, PAGES, resolve_location


@pytest.mark.parametrize("page", PAGES)
def test_public_page_slugs_resolve_with_a_recorded_pitch(page):
    assert resolve_location(PAGE_SLUGS[page], "recorded-a", ["recorded-a", "recorded-b"]) == (
        page,
        "recorded-a",
    )


@pytest.mark.parametrize("pitch", [None, "", "../private", "/tmp/file", "unknown", 123])
def test_invalid_public_pitch_values_do_not_select_another_pitch(pitch):
    assert resolve_location("explore", pitch, ["recorded-a"])[1] is None


def test_unknown_page_uses_the_opening_without_treating_url_as_instructions():
    assert resolve_location("<script>alert(1)</script>", "recorded-a", ["recorded-a"]) == (
        PAGES[0],
        "recorded-a",
    )
