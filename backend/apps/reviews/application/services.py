"""Use cases of the Reviews bounded context.

Three audiences meet in one service, and the method names say which is which.
``page_of`` / ``update_page`` / ``own_reviews`` / ``remove`` are the organizer's;
``public_page`` and ``submit`` are the stranger's, reached with no credential but
the slug; ``all_reviews`` is the platform operator's, and it is the single read
here that is not scoped to one organization.

The organizer never *creates* their page — ``page_of`` mints one the first time
they open the screen. A "create the page" step would be a button whose only
purpose is to enable the button beside it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Final

from apps.reviews.application.commands import SubmitReviewCommand, UpdateReviewPageCommand
from apps.reviews.application.dto import FestivalOption, PublicPageView, ReviewPageView, ReviewView
from apps.reviews.application.interfaces import (
    Clock,
    FestivalCatalog,
    OrganizationDirectory,
    ReviewPageRepository,
    ReviewRepository,
    SlugFactory,
    UuidGenerator,
)
from apps.reviews.domain.entities import Review, ReviewPage
from apps.reviews.domain.exceptions import (
    InvalidReviewDataError,
    ReviewNotFoundError,
    ReviewPageNotFoundError,
    SlugUnavailableError,
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

__all__ = ["ReviewService"]

#: How many times a fresh slug is tried before giving up. At ~57 bits each, a
#: second attempt is already the sign of something other than a collision.
_SLUG_ATTEMPTS: Final = 5

#: The operator's console and the organizer's list are both read wholesale; this
#: caps the page so one organization with a viral banner cannot serve a response
#: nobody can render.
_LIST_LIMIT: Final = 500


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidReviewDataError(f"Некорректный {what}.") from exc


class ReviewService:
    """Every Reviews use case, over its two repositories and two read ports."""

    def __init__(
        self,
        *,
        pages: ReviewPageRepository,
        reviews: ReviewRepository,
        clock: Clock,
        uuids: UuidGenerator,
        slugs: SlugFactory,
        festivals: FestivalCatalog,
        organizations: OrganizationDirectory,
    ) -> None:
        self._pages = pages
        self._reviews = reviews
        self._clock = clock
        self._uuids = uuids
        self._slugs = slugs
        self._festivals = festivals
        self._organizations = organizations

    # ------------------------------------------------------------------
    # The organizer
    # ------------------------------------------------------------------

    def page_of(self, organization_id: uuid.UUID) -> ReviewPageView:
        """This organization's page, minted on first sight.

        Creating it lazily is what makes the link permanent in practice: it comes
        into existence once, the first time anybody opens the screen, and no later
        action in the workspace can replace it with a second one.
        """
        page = self._pages.get_for_organization(organization_id)
        if page is None:
            now = self._clock.utcnow()
            page = ReviewPage.open_for(
                page_id=self._uuids.new(),
                organization_id=organization_id,
                slug=self._mint_slug(),
                now=now,
            )
            self._pages.save(page)
        return self._page_view(page)

    def update_page(self, command: UpdateReviewPageCommand) -> ReviewPageView:
        """Reword the page, or start and stop collecting."""
        organization_id = _uuid(command.organization_id, what="идентификатор организации")
        page = self._pages.get_for_organization(organization_id)
        if page is None:
            raise ReviewPageNotFoundError("Страница отзывов ещё не создана.")
        now = self._clock.utcnow()
        if command.title is not None or command.intro is not None:
            page.rewrite(
                title=PageTitle(command.title) if command.title is not None else None,
                intro=PageIntro(command.intro) if command.intro is not None else None,
                now=now,
            )
        if command.accepting is not None:
            if command.accepting:
                page.start_collecting(now=now)
            else:
                page.stop_collecting(now=now)
        self._pages.save(page)
        return self._page_view(page)

    def own_reviews(self, organization_id: uuid.UUID) -> Sequence[ReviewView]:
        """Everything left on this organization's page, newest first."""
        return [self._review_view(review) for review in self._reviews.list_for_organization(organization_id, limit=_LIST_LIMIT)]

    def remove(self, review_id: uuid.UUID, *, organization_id: uuid.UUID | None = None) -> None:
        """Delete a note.

        ``organization_id`` is the caller's own when an organizer is deleting, and
        ``None`` for the platform operator. Another organization's note is reported
        as *not found* rather than as forbidden: confirming that an id exists is
        already telling one organization something about another.
        """
        review = self._reviews.get(review_id)
        if review is None or (organization_id is not None and review.organization_id != organization_id):
            raise ReviewNotFoundError("Отзыв не найден.")
        self._reviews.soft_delete(review, now=self._clock.utcnow())

    # ------------------------------------------------------------------
    # The platform operator
    # ------------------------------------------------------------------

    def all_reviews(self) -> Sequence[ReviewView]:
        """Every note on the platform, newest first, each named with its organization.

        The one read here that crosses organizations. It exists so a complaint
        about what somebody wrote can be looked at by the only party above both
        sides of it.
        """
        reviews = self._reviews.list_everywhere(limit=_LIST_LIMIT)
        names: dict[uuid.UUID, str | None] = {}
        for review in reviews:
            if review.organization_id not in names:
                names[review.organization_id] = self._organizations.name_of(review.organization_id)
        return [self._review_view(review, organization_name=names.get(review.organization_id)) for review in reviews]

    # ------------------------------------------------------------------
    # The stranger with a phone
    # ------------------------------------------------------------------

    def public_page(self, slug: str) -> PublicPageView:
        """The page behind a scanned code.

        A closed page answers too, with ``accepting`` false — the banner is already
        printed, and somebody who walked over to it deserves a sentence rather than
        a 404. A page that never existed, or whose organization was removed, is
        indistinguishable from one that was never printed.
        """
        page = self._pages.find_by_slug(str(slug).strip())
        if page is None:
            raise ReviewPageNotFoundError("Страница отзывов не найдена.")
        return PublicPageView(
            slug=page.slug.value,
            title=page.title.value,
            intro=page.intro.value,
            accepting=page.accepting,
            festivals=tuple(
                FestivalOption(id=str(festival.id), title=festival.title) for festival in self._festivals.festivals_of(page.organization_id)
            ),
        )

    def submit(self, command: SubmitReviewCommand) -> ReviewView:
        """Accept a note left through the public page.

        The festival, when one is named, is checked against the *page's* own
        organization and not merely parsed: otherwise anybody holding a link could
        file notes against a festival belonging to somebody else. An id that does
        not survive that check is dropped rather than refused — the note is what
        the person came to leave, and losing it over a stale option in a picker
        would be the wrong trade.
        """
        page = self._pages.find_by_slug(str(command.slug).strip())
        if page is None:
            raise ReviewPageNotFoundError("Страница отзывов не найдена.")
        page.ensure_accepting()

        photos = [PhotoReference(reference) for reference in command.photos]
        if len(photos) > PHOTOS_MAX:
            raise InvalidReviewDataError(f"К отзыву можно приложить не больше {PHOTOS_MAX} фотографий.")

        competition_id: uuid.UUID | None = None
        competition_title = ""
        if command.competition_id:
            candidate = _uuid(command.competition_id, what="фестиваль")
            title = self._festivals.title_of(candidate, organization_id=page.organization_id)
            if title is not None:
                competition_id = candidate
                competition_title = title

        now = self._clock.utcnow()
        review = Review.leave(
            review_id=self._uuids.new(),
            page=page,
            text=ReviewText(command.text),
            consent=ConsentRecord(code=command.consent_code, version=command.consent_version, accepted_at=now),
            now=now,
            author=AuthorName.parse(command.author_name),
            competition_id=competition_id,
            competition_title=competition_title,
            photos=photos,
        )
        self._reviews.add(review)
        return self._review_view(review)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _mint_slug(self) -> PublicSlug:
        for _ in range(_SLUG_ATTEMPTS):
            candidate = self._slugs.new_slug()
            if not self._pages.slug_exists(candidate):
                return PublicSlug(candidate)
        raise SlugUnavailableError("Не удалось создать ссылку на страницу отзывов. Попробуйте ещё раз.")

    def _page_view(self, page: ReviewPage) -> ReviewPageView:
        return ReviewPageView(
            id=str(page.id),
            organization_id=str(page.organization_id),
            slug=page.slug.value,
            title=page.title.value,
            intro=page.intro.value,
            accepting=page.accepting,
            created_at=page.created_at,
            updated_at=page.updated_at,
            review_count=self._reviews.count_for_organization(page.organization_id),
        )

    def _review_view(self, review: Review, *, organization_name: str | None = None) -> ReviewView:
        return ReviewView(
            id=str(review.id),
            organization_id=str(review.organization_id),
            author_name=review.author.value if review.author is not None else None,
            text=review.text.value,
            photos=tuple(photo.value for photo in review.photos),
            competition_id=str(review.competition_id) if review.competition_id is not None else None,
            competition_title=review.competition_title or None,
            submitted_at=review.submitted_at,
            consent_code=review.consent.code,
            consent_version=review.consent.version,
            consent_accepted_at=review.consent.accepted_at,
            organization_name=organization_name,
        )
