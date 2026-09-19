"""The two aggregates of the Reviews context: the page, and a note left on it.

They are separate roots on purpose. A :class:`ReviewPage` is one row per
organization that changes a few times a year — a heading, a paragraph, whether
collection is open. A :class:`Review` is appended by strangers, never edited, and
there may be thousands; making them children of the page would mean loading every
note the organizer has ever received in order to accept one more (ARCH-001 §13.4,
the same reasoning that keeps votes out of the ``Ballot``).

What a review holds is a **copy**, not a reference. The festival it names is kept
as an id *and* its title at the moment of writing: a note that says "спасибо за
«Весенние голоса»" must still say that after the festival is renamed or removed,
and a card that resolved the name live would quietly rewrite what somebody said.

Framework-free (no Django, no DRF, no clock, no IO): time always arrives as ``now``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from typing import Final

from .exceptions import InvalidReviewDataError, ReviewPageClosedError
from .value_objects import (
    PHOTOS_MAX,
    AuthorName,
    ConsentRecord,
    PageIntro,
    PageTitle,
    PhotoReference,
    PublicSlug,
    ReviewText,
)

__all__ = ["Review", "ReviewPage"]

#: Opaque capability token proving construction went through a factory.
_CREATION_TOKEN: Final = object()

#: What the page says before anybody has rewritten it.
DEFAULT_PAGE_TITLE: Final = "Оставьте отзыв"


@dataclass(slots=True, eq=False, repr=False)
class ReviewPage:
    """What a visitor reaches by scanning the code on a banner.

    One per organization, and its slug never changes: the banner is printed on
    cloth and will stand at next season's events too. Everything else about the
    page is editable, including whether it still accepts notes — an organizer who
    has finished collecting closes it, and the link then explains itself instead of
    dying.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _organization_id: uuid.UUID
    _slug: PublicSlug
    _title: PageTitle
    _created_at: datetime
    _updated_at: datetime
    _intro: PageIntro = field(default_factory=PageIntro)
    _accepting: bool = True
    _version: int = 1
    #: The version this aggregate was last read at, or ``None`` for one never stored.
    _persisted_version: int | None = None

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidReviewDataError("ReviewPage must be created via open_for() or rehydrate().")

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def open_for(
        cls,
        *,
        page_id: uuid.UUID,
        organization_id: uuid.UUID,
        slug: PublicSlug,
        now: datetime,
        title: PageTitle | None = None,
        intro: PageIntro | None = None,
    ) -> ReviewPage:
        """Start an organization's page, already collecting.

        Created open rather than as a draft: unlike a ballot there is nothing to
        assemble first, and a page that had to be published before it worked would
        be a step whose only effect is a banner that leads nowhere.
        """
        return cls(
            _token=_CREATION_TOKEN,
            _id=page_id,
            _organization_id=organization_id,
            _slug=slug,
            _title=title or PageTitle(DEFAULT_PAGE_TITLE),
            _created_at=now,
            _updated_at=now,
            _intro=intro or PageIntro(),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        page_id: uuid.UUID,
        organization_id: uuid.UUID,
        slug: PublicSlug,
        title: PageTitle,
        created_at: datetime,
        updated_at: datetime,
        intro: PageIntro | None = None,
        accepting: bool = True,
        version: int = 1,
    ) -> ReviewPage:
        """Rebuild a stored page without re-running its creation rules."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=page_id,
            _organization_id=organization_id,
            _slug=slug,
            _title=title,
            _created_at=created_at,
            _updated_at=updated_at,
            _intro=intro or PageIntro(),
            _accepting=accepting,
            _version=version,
            _persisted_version=version,
        )

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def rewrite(self, *, title: PageTitle | None = None, intro: PageIntro | None = None, now: datetime) -> None:
        """Change the wording a visitor reads."""
        if title is not None:
            self._title = title
        if intro is not None:
            self._intro = intro
        self._touch(now)

    def start_collecting(self, *, now: datetime) -> None:
        """Accept notes again. Idempotent — reopening an open page is not an error."""
        self._accepting = True
        self._touch(now)

    def stop_collecting(self, *, now: datetime) -> None:
        """Stop accepting, without breaking the printed link.

        The page still answers; it simply says the collection is closed. Notes
        already left are untouched — closing is not a retraction of what people
        wrote.
        """
        self._accepting = False
        self._touch(now)

    def ensure_accepting(self) -> None:
        """Raise unless a note may be left right now."""
        if not self._accepting:
            raise ReviewPageClosedError("Организатор больше не собирает отзывы по этой ссылке.")

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def organization_id(self) -> uuid.UUID:
        return self._organization_id

    @property
    def slug(self) -> PublicSlug:
        return self._slug

    @property
    def title(self) -> PageTitle:
        return self._title

    @property
    def intro(self) -> PageIntro:
        return self._intro

    @property
    def accepting(self) -> bool:
        return self._accepting

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def persisted_version(self) -> int | None:
        return self._persisted_version

    def mark_persisted(self) -> None:
        """Called by the repository once the row matches this aggregate."""
        self._persisted_version = self._version


@dataclass(slots=True, eq=False, repr=False)
class Review:
    """One note somebody left, with the consent that allows it to be kept.

    Immutable once written. There is no ``edit``: the author is a stranger who will
    never come back, and an organizer able to correct what the audience said would
    be holding something other than a review. The only thing that ever happens to a
    note afterwards is removal, and that is the repository's soft delete.

    ``consent`` is not decoration. :meth:`leave` will not construct a review
    without one, so the legal basis for holding the name, the words and the
    photographs is a column on the row rather than a promise about the form
    (LEGAL-001 §13.3).
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _page_id: uuid.UUID
    #: Denormalized from the page: every read of these — the organizer's list, the
    #: operator's console — is scoped by organization, and resolving the page for
    #: each row to learn whose it is would be a join in service of nothing.
    _organization_id: uuid.UUID
    _text: ReviewText
    _consent: ConsentRecord
    _submitted_at: datetime
    _author: AuthorName | None = None
    #: The festival the note is about, when the author picked one. Id *and* frozen
    #: title, because the title has to survive the festival.
    _competition_id: uuid.UUID | None = None
    _competition_title: str = ""
    _photos: list[PhotoReference] = field(default_factory=list)
    _version: int = 1
    _persisted_version: int | None = None

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidReviewDataError("Review must be created via leave() or rehydrate().")
        if len(self._photos) > PHOTOS_MAX:
            raise InvalidReviewDataError(f"К отзыву можно приложить не больше {PHOTOS_MAX} фотографий.")

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def leave(
        cls,
        *,
        review_id: uuid.UUID,
        page: ReviewPage,
        text: ReviewText,
        consent: ConsentRecord,
        now: datetime,
        author: AuthorName | None = None,
        competition_id: uuid.UUID | None = None,
        competition_title: str = "",
        photos: Iterable[PhotoReference] = (),
    ) -> Review:
        """Write a note on ``page``, refusing if it has stopped collecting.

        The page is passed whole rather than as an id so the closed check cannot be
        forgotten by a caller that happens to know the id — leaving a note on a
        page and checking that the page is open are the same act.
        """
        page.ensure_accepting()
        return cls(
            _token=_CREATION_TOKEN,
            _id=review_id,
            _page_id=page.id,
            _organization_id=page.organization_id,
            _text=text,
            _consent=consent,
            _submitted_at=now,
            _author=author,
            _competition_id=competition_id,
            _competition_title=competition_title.strip() if competition_id is not None else "",
            _photos=list(photos),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        review_id: uuid.UUID,
        page_id: uuid.UUID,
        organization_id: uuid.UUID,
        text: ReviewText,
        consent: ConsentRecord,
        submitted_at: datetime,
        author: AuthorName | None = None,
        competition_id: uuid.UUID | None = None,
        competition_title: str = "",
        photos: Iterable[PhotoReference] = (),
        version: int = 1,
    ) -> Review:
        """Rebuild a stored note without re-running the rules that let it in."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=review_id,
            _page_id=page_id,
            _organization_id=organization_id,
            _text=text,
            _consent=consent,
            _submitted_at=submitted_at,
            _author=author,
            _competition_id=competition_id,
            _competition_title=competition_title,
            _photos=list(photos),
            _version=version,
            _persisted_version=version,
        )

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def page_id(self) -> uuid.UUID:
        return self._page_id

    @property
    def organization_id(self) -> uuid.UUID:
        return self._organization_id

    @property
    def text(self) -> ReviewText:
        return self._text

    @property
    def consent(self) -> ConsentRecord:
        return self._consent

    @property
    def submitted_at(self) -> datetime:
        return self._submitted_at

    @property
    def author(self) -> AuthorName | None:
        return self._author

    @property
    def competition_id(self) -> uuid.UUID | None:
        return self._competition_id

    @property
    def competition_title(self) -> str:
        return self._competition_title

    @property
    def photos(self) -> Sequence[PhotoReference]:
        return tuple(self._photos)

    @property
    def version(self) -> int:
        return self._version

    @property
    def persisted_version(self) -> int | None:
        return self._persisted_version

    def mark_persisted(self) -> None:
        """Called by the repository once the row matches this aggregate."""
        self._persisted_version = self._version
