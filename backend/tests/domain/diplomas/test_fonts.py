"""Domain tests for the font vocabulary (no Django, no reportlab)."""

from __future__ import annotations

import pytest

from apps.diplomas.domain.fonts import (
    CYRILLIC_SAMPLE,
    FAMILY_ALIASES,
    FontVariant,
    normalize_family,
)


class TestFontVariant:
    @pytest.mark.parametrize(
        ("bold", "italic", "expected"),
        [
            (False, False, FontVariant.REGULAR),
            (True, False, FontVariant.BOLD),
            (False, True, FontVariant.ITALIC),
            (True, True, FontVariant.BOLD_ITALIC),
        ],
    )
    def test_a_bold_italic_pair_names_one_face(self, bold: bool, italic: bool, expected: FontVariant) -> None:
        assert FontVariant.of(bold=bold, italic=italic) is expected

    def test_a_variant_knows_its_own_weight_and_slant(self) -> None:
        assert FontVariant.BOLD_ITALIC.bold and FontVariant.BOLD_ITALIC.italic
        assert FontVariant.BOLD.bold and not FontVariant.BOLD.italic
        assert not FontVariant.REGULAR.bold and not FontVariant.REGULAR.italic

    def test_the_names_are_the_bundled_filename_suffixes(self) -> None:
        # The enum *is* the naming convention bundled faces are discovered by, so a rename
        # here would silently stop a whole directory of files from being found.
        assert {variant.value for variant in FontVariant} == {"Regular", "Bold", "Italic", "BoldItalic"}

    def test_a_missing_face_falls_back_within_its_own_family(self) -> None:
        # The family is what the organizer chose; the weight is a detail of it. Falling back
        # to another family would change the document more than dropping the weight does.
        assert FontVariant.BOLD_ITALIC.fallbacks == (FontVariant.BOLD, FontVariant.ITALIC, FontVariant.REGULAR)
        assert FontVariant.BOLD.fallbacks == (FontVariant.REGULAR,)
        assert FontVariant.ITALIC.fallbacks == (FontVariant.REGULAR,)

    def test_regular_has_nothing_to_fall_back_to(self) -> None:
        assert FontVariant.REGULAR.fallbacks == ()


class TestNormalizeFamily:
    @pytest.mark.parametrize("spelling", ["PT Sans", "PTSans", "pt sans", "  pt   sans  "])
    def test_one_family_under_many_spellings(self, spelling: str) -> None:
        # A template stores what the editor put in it, a filename cannot hold a space, and an
        # uploaded file names itself however its designer chose.
        assert normalize_family(spelling) == "ptsans"


class TestAliases:
    @pytest.mark.parametrize("proprietary", ["arial", "timesnewroman", "georgia"])
    def test_every_unshippable_name_has_a_substitute(self, proprietary: str) -> None:
        assert proprietary in FAMILY_ALIASES
        assert FAMILY_ALIASES[proprietary]

    def test_arial_and_times_map_to_their_metric_compatible_twins(self) -> None:
        # Metric-compatible matters: a template laid out against Arial keeps its line breaks.
        assert FAMILY_ALIASES["arial"] == "Liberation Sans"
        assert FAMILY_ALIASES["timesnewroman"] == "Liberation Serif"

    def test_no_alias_points_at_another_alias(self) -> None:
        # A chain would resolve differently depending on how many hops the lookup makes.
        targets = {normalize_family(target) for target in FAMILY_ALIASES.values()}
        assert targets.isdisjoint(FAMILY_ALIASES.keys())

    def test_alias_keys_are_already_normalized(self) -> None:
        # They are looked up by a normalized family name, so an unnormalized key is dead.
        assert all(key == normalize_family(key) for key in FAMILY_ALIASES)


class TestCyrillicSample:
    def test_the_sample_is_the_whole_russian_alphabet_in_both_cases(self) -> None:
        assert len(CYRILLIC_SAMPLE) == 66
        assert "ё" in CYRILLIC_SAMPLE and "Ё" in CYRILLIC_SAMPLE
        assert "ъ" in CYRILLIC_SAMPLE and "Ы" in CYRILLIC_SAMPLE
