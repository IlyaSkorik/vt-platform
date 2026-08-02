"""Unit tests for the shared slugger.

Two contexts derive public addresses with this — an organization's and a
competition's — so its edges are worth pinning: what happens to Belarusian
letters, to a title that transliterates to nothing, and to the second festival
that wants an address the first one took.
"""

from __future__ import annotations

import pytest

from shared.utils.slugs import slugify, unique_slug


class TestSlugify:
    def test_transliterates_russian(self) -> None:
        assert slugify("Взлёт талантов", fallback="x") == "vzlet-talantov"

    def test_transliterates_the_belarusian_letters(self) -> None:
        # ў and і are not in the Russian alphabet, and dropping them would turn
        # "Беларусь" into an address missing a letter rather than a wrong one.
        assert slugify("Здароўе і моладзь", fallback="x") == "zdaroue-i-moladz"

    def test_collapses_punctuation_and_spacing(self) -> None:
        assert slugify("  Весенний   вокал — 2026!  ", fallback="x") == "vesenniy-vokal-2026"

    def test_keeps_latin_and_digits_as_they_are(self) -> None:
        assert slugify("Open Air 2026", fallback="x") == "open-air-2026"

    def test_falls_back_when_nothing_survives(self) -> None:
        # An emoji-only title yields an empty segment, and an empty segment in a
        # URL silently becomes the parent path — the catalog, not the festival.
        assert slugify("🎵🎶", fallback="competition-abc") == "competition-abc"

    def test_truncates_without_leaving_a_trailing_dash(self) -> None:
        result = slugify("а" * 40 + " " + "б" * 40, fallback="x", max_length=20)

        assert len(result) <= 20
        assert not result.endswith("-")


class TestUniqueSlug:
    def test_gives_the_clean_address_to_the_first_claimant(self) -> None:
        assert unique_slug("Весенний вокал", fallback="x", is_taken=lambda _: False) == "vesenniy-vokal"

    def test_numbers_a_collision(self) -> None:
        taken = {"vesenniy-vokal"}

        assert unique_slug("Весенний вокал", fallback="x", is_taken=taken.__contains__) == "vesenniy-vokal-2"

    def test_keeps_counting_past_the_first_collision(self) -> None:
        taken = {"vesenniy-vokal", "vesenniy-vokal-2", "vesenniy-vokal-3"}

        assert unique_slug("Весенний вокал", fallback="x", is_taken=taken.__contains__) == "vesenniy-vokal-4"

    def test_trims_the_stem_rather_than_the_suffix(self) -> None:
        # A truncated "-12" would be "-1", a different and possibly taken address.
        taken = {"aaaaaaaaaa"}
        result = unique_slug("а" * 20, fallback="x", is_taken=taken.__contains__, max_length=10)

        assert len(result) <= 10
        assert result.endswith("-2")

    def test_gives_up_rather_than_spinning_forever(self) -> None:
        with pytest.raises(RuntimeError):
            unique_slug("Весенний вокал", fallback="x", is_taken=lambda _: True)
