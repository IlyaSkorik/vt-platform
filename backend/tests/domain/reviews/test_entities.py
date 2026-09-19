"""Правила, на которых держится отзыв, — без базы и без HTTP.

Здесь закреплено то, что не должно зависеть от того, какой край спросил: отзыв
без согласия не собирается вообще, закрытая страница не принимает заметок, имя
необязательно, а перенос строки — часть того, что человек написал.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.reviews.domain.entities import Review, ReviewPage
from apps.reviews.domain.exceptions import (
    ConsentRequiredError,
    InvalidReviewDataError,
    ReviewPageClosedError,
)
from apps.reviews.domain.value_objects import (
    PHOTOS_MAX,
    AuthorName,
    ConsentRecord,
    PageIntro,
    PageTitle,
    PhotoReference,
    PublicSlug,
    ReviewText,
)

_NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def _page(*, accepting: bool = True) -> ReviewPage:
    page = ReviewPage.open_for(
        page_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        slug=PublicSlug.generate(),
        now=_NOW,
    )
    if not accepting:
        page.stop_collecting(now=_NOW)
    return page


def _consent() -> ConsentRecord:
    return ConsentRecord(code="review_personal_data", version="1.0", accepted_at=_NOW)


class TestTheConsent:
    def test_a_review_cannot_exist_without_one(self) -> None:
        """Согласие — основание хранить запись, а не галочка на форме."""
        with pytest.raises(ConsentRequiredError):
            ConsentRecord(code="review_personal_data", version="   ", accepted_at=_NOW)

    def test_the_version_travels_with_the_note(self) -> None:
        review = Review.leave(
            review_id=uuid.uuid4(),
            page=_page(),
            text=ReviewText("Спасибо!"),
            consent=_consent(),
            now=_NOW,
        )

        assert review.consent.code == "review_personal_data"
        assert review.consent.version == "1.0"
        assert review.consent.accepted_at == _NOW

    def test_a_naive_moment_is_refused(self) -> None:
        """Момент согласия без часового пояса нечем подтвердить."""
        with pytest.raises(InvalidReviewDataError):
            ConsentRecord(code="review_personal_data", version="1.0", accepted_at=datetime(2026, 9, 19, 12, 0))


class TestThePage:
    def test_it_starts_collecting(self) -> None:
        assert _page().accepting is True

    def test_a_closed_page_refuses_a_note(self) -> None:
        with pytest.raises(ReviewPageClosedError):
            Review.leave(
                review_id=uuid.uuid4(),
                page=_page(accepting=False),
                text=ReviewText("Спасибо!"),
                consent=_consent(),
                now=_NOW,
            )

    def test_closing_is_not_a_retraction(self) -> None:
        """Закрытие останавливает приём, но не трогает уже написанное."""
        page = _page()
        review = Review.leave(review_id=uuid.uuid4(), page=page, text=ReviewText("Спасибо!"), consent=_consent(), now=_NOW)

        page.stop_collecting(now=_NOW)

        assert review.text.value == "Спасибо!"

    def test_reopening_an_open_page_is_not_an_error(self) -> None:
        page = _page()

        page.start_collecting(now=_NOW)

        assert page.accepting is True

    def test_rewording_leaves_the_link_alone(self) -> None:
        page = _page()
        slug = page.slug.value

        page.rewrite(title=PageTitle("Как вам фестиваль?"), intro=PageIntro("Пара слов."), now=_NOW)

        assert page.slug.value == slug


class TestWhatWasWritten:
    def test_the_name_is_optional(self) -> None:
        assert AuthorName.parse("") is None
        assert AuthorName.parse("   ") is None
        assert AuthorName.parse(None) is None
        assert AuthorName.parse(" Мария ").value == "Мария"  # type: ignore[union-attr]

    def test_an_empty_note_is_refused(self) -> None:
        with pytest.raises(InvalidReviewDataError):
            ReviewText("   \n  ")

    def test_line_breaks_survive(self) -> None:
        """Три благодарности по строке — это три строки, а не абзац."""
        text = ReviewText("Спасибо Ирине\nСпасибо Олегу\nСпасибо всем")

        assert text.value.count("\n") == 2

    def test_a_sixth_photograph_is_refused(self) -> None:
        with pytest.raises(InvalidReviewDataError):
            Review.leave(
                review_id=uuid.uuid4(),
                page=_page(),
                text=ReviewText("Спасибо!"),
                consent=_consent(),
                now=_NOW,
                photos=[PhotoReference(f"reviews/x/{index}.jpg") for index in range(PHOTOS_MAX + 1)],
            )

    def test_a_festival_title_is_only_kept_with_its_id(self) -> None:
        """Название без ссылки на фестиваль — строка, за которой ничего не стоит."""
        review = Review.leave(
            review_id=uuid.uuid4(),
            page=_page(),
            text=ReviewText("Спасибо!"),
            consent=_consent(),
            now=_NOW,
            competition_title="Весенние голоса",
        )

        assert review.competition_id is None
        assert review.competition_title == ""


class TestTheSlug:
    def test_it_avoids_confusable_characters(self) -> None:
        """Ссылку набирают с баннера, а его читают с расстояния."""
        for _ in range(50):
            value = PublicSlug.generate().value
            assert not set(value) & set("O0Il1")

    def test_it_refuses_something_that_is_not_one(self) -> None:
        with pytest.raises(InvalidReviewDataError):
            PublicSlug("нет")
