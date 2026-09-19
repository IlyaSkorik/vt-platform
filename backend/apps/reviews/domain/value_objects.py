"""Value objects for the Reviews bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

Identifiers stay plain :class:`uuid.UUID` values, as in Voting: this context holds
its own ids and id-only references outward (``organization_id``, ``competition_id``),
and none of them carries behaviour worth a type. What does carry rules is the
wording on the page, what a visitor may write, how many photographs they may
attach, and the consent the whole record rests on.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from .exceptions import ConsentRequiredError, InvalidReviewDataError

__all__ = [
    "AUTHOR_NAME_MAX",
    "PAGE_INTRO_MAX",
    "PAGE_TITLE_MAX",
    "PHOTOS_MAX",
    "PHOTO_REFERENCE_MAX",
    "REVIEW_TEXT_MAX",
    "AuthorName",
    "ConsentRecord",
    "PageIntro",
    "PageTitle",
    "PhotoReference",
    "PublicSlug",
    "ReviewText",
]

PAGE_TITLE_MAX: Final = 200
PAGE_INTRO_MAX: Final = 1000
AUTHOR_NAME_MAX: Final = 120
PHOTO_REFERENCE_MAX: Final = 1024

#: The longest note the page accepts.
#:
#: Generous rather than tight: this is somebody typing on a phone in a foyer, and
#: a limit they can hit by saying what they came to say is a limit that edits them.
REVIEW_TEXT_MAX: Final = 4000

#: How many photographs travel with one note.
#:
#: A bound on an anonymous upload before it is anything else. Five is more than
#: anybody attaches from a hall and far below what would make the form worth
#: pointing a script at.
PHOTOS_MAX: Final = 5

#: The public slug alphabet: no characters that can be misread for one another,
#: because these links are typed off banners and read aloud.
_SLUG_ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_SLUG_LENGTH: Final = 10
_SLUG_MIN_LENGTH: Final = 6
_SLUG_MAX_LENGTH: Final = 64


def _clean(value: str, *, maximum: int, what: str) -> str:
    text = " ".join(str(value).split()).strip()
    if not text:
        raise InvalidReviewDataError(f"{what} не может быть пустым.")
    if len(text) > maximum:
        raise InvalidReviewDataError(f"{what} — не длиннее {maximum} символов.")
    return text


@dataclass(frozen=True, slots=True)
class PublicSlug:
    """The unguessable token in a review URL (``/reviews/AbX82K``).

    The slug *is* the credential: the page carries no authentication, so it is
    minted from a confusable-free alphabet with enough entropy that a link cannot
    be found by trying, and it is never derived from the organization's name.

    Deliberately a copy of the Voting context's value object rather than an import
    of it: the two contexts share no domain edge (ARCH-001 §14), and a little
    duplication is cheaper than a dependency between them.

    A page's slug is permanent. The banner carrying it is printed on cloth.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = str(self.value).strip()
        if not (_SLUG_MIN_LENGTH <= len(stripped) <= _SLUG_MAX_LENGTH):
            raise InvalidReviewDataError(f"Адрес ссылки — от {_SLUG_MIN_LENGTH} до {_SLUG_MAX_LENGTH} символов.")
        if any(character not in _SLUG_ALPHABET for character in stripped):
            raise InvalidReviewDataError("В адресе ссылки допустимы только однозначные латинские символы и цифры.")
        object.__setattr__(self, "value", stripped)

    @classmethod
    def generate(cls) -> PublicSlug:
        """Mint a fresh random slug (~57 bits of entropy at the default length)."""
        return cls("".join(secrets.choice(_SLUG_ALPHABET) for _ in range(_SLUG_LENGTH)))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PageTitle:
    """The heading a visitor reads after scanning the code."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clean(self.value, maximum=PAGE_TITLE_MAX, what="Заголовок страницы"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PageIntro:
    """The paragraph under the heading, if the organizer wrote one.

    Blank is the normal case and not an error: the default page says enough.
    """

    value: str = ""

    def __post_init__(self) -> None:
        text = str(self.value).strip()
        if len(text) > PAGE_INTRO_MAX:
            raise InvalidReviewDataError(f"Текст под заголовком — не длиннее {PAGE_INTRO_MAX} символов.")
        object.__setattr__(self, "value", text)

    @property
    def empty(self) -> bool:
        return not self.value

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AuthorName:
    """How the author signed the note, when they signed it at all.

    Optional by design, and the type says so: :meth:`parse` answers ``None`` for a
    blank, so "anonymous" is an absent value everywhere downstream rather than an
    empty string one screen remembers to special-case. An unsigned note is the
    ordinary case — asking for a name is how you stop getting the honest ones.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clean(self.value, maximum=AUTHOR_NAME_MAX, what="Имя"))

    @classmethod
    def parse(cls, value: str | None) -> AuthorName | None:
        """Build a name, or ``None`` when nothing was typed."""
        if value is None or not str(value).strip():
            return None
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ReviewText:
    """What the person actually wrote — the one field the form insists on.

    Newlines survive: somebody thanking three people by name puts each on its own
    line, and collapsing that into a paragraph rewrites what they said. Only runs
    of blank lines and trailing whitespace are tidied.
    """

    value: str

    def __post_init__(self) -> None:
        lines = [" ".join(line.split()) for line in str(self.value).splitlines()]
        text = "\n".join(lines).strip("\n").strip()
        if not text:
            raise InvalidReviewDataError("Напишите отзыв — это единственное обязательное поле.")
        if len(text) > REVIEW_TEXT_MAX:
            raise InvalidReviewDataError(f"Отзыв — не длиннее {REVIEW_TEXT_MAX} символов.")
        object.__setattr__(self, "value", text)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PhotoReference:
    """Where one attached photograph is stored, as the storage names it."""

    value: str

    def __post_init__(self) -> None:
        text = str(self.value).strip()
        if not text:
            raise InvalidReviewDataError("Ссылка на фотографию не может быть пустой.")
        if len(text) > PHOTO_REFERENCE_MAX:
            raise InvalidReviewDataError("Слишком длинная ссылка на фотографию.")
        object.__setattr__(self, "value", text)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    """The permission this record rests on: which consent, which wording, accepted when.

    A ``(code, version)`` pair, the same shape the rest of the platform records a
    consent in — the code says *what* was agreed to, the version says which
    wording of it. Consent texts are append-only, so new wording gets a new
    version; storing both is what makes "what did this person agree to?"
    answerable years later from the row itself rather than from whatever the form
    happens to say today (LEGAL-001 §13.3).
    """

    code: str
    version: str
    accepted_at: datetime

    def __post_init__(self) -> None:
        code = str(self.code).strip()
        version = str(self.version).strip()
        if not code or not version:
            raise ConsentRequiredError("Без согласия на обработку персональных данных отзыв не сохраняется.")
        if len(code) > 64 or len(version) > 64:
            raise InvalidReviewDataError("Слишком длинное обозначение согласия.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "version", version)
        if self.accepted_at.tzinfo is None:
            raise InvalidReviewDataError("Момент согласия должен быть с часовым поясом.")
