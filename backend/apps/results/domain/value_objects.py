"""Value objects for the Results bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

The one that matters is the **award**, and what it is deserves stating precisely. A
result in this platform is not a place and not a score: the jury says "Лауреат II
степени" and that is the whole of it. There is no first, second and third within a
degree and nothing to tie-break - which is why the Diplomas context stores a diploma's
result as a single ``award.degree`` string and knows nothing about ranking.

A row therefore stores an award **code**: a short, stable token like ``LAUREATE_II``.
What that code is *called* is the festival's own business, because festivals genuinely
disagree - one hands out "Лауреат I степени", the next "1 место", the next both a
"Гран-при" and a "Лауреат". The vocabulary each festival draws from is configured in
the Judging context and resolved through
:class:`~apps.results.application.interfaces.AwardVocabulary`; :class:`AwardKind` below
is the **default** every festival starts with, and the fallback for a code whose tier
has since been deleted from a scale. A published protocol must keep naming its awards
the way it named them when it was published, so a code with no tier behind it is
rendered from that fallback rather than left blank.

Identifiers are plain :class:`uuid.UUID` values rather than one wrapper class per
reference, the way the Programs context does it: this context holds ids only - its
own, and ``competition_id`` / ``nomination_id`` / ``submission_id`` pointing at other
contexts - and none of them carry behaviour worth a type of their own.
"""

from __future__ import annotations

import re
import secrets
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .exceptions import InvalidProtocolDataError

__all__ = [
    "AWARD_LABELS",
    "AWARD_ORDER",
    "COLUMN_LABELS",
    "DEFAULT_PUBLIC_COLUMNS",
    "AwardCode",
    "AwardKind",
    "ProtocolColumn",
    "ProtocolName",
    "ProtocolStatus",
    "PublicSlug",
    "PublishedResult",
    "PublishedSnapshot",
    "default_award_label",
    "parse_award",
    "parse_columns",
]

#: An award code as a protocol stores it. A plain string on purpose: the vocabulary is
#: the festival's, so there is no enum this context could check it against.
AwardCode = str

_NAME_MAX: Final = 200

#: The shape of an award code - what :func:`parse_award` accepts. Matches the codes the
#: Judging context mints, so the two never drift into accepting different things.
_AWARD_CODE_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

_SLUG_ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_SLUG_LENGTH: Final = 10
_SLUG_MIN_LENGTH: Final = 6
_SLUG_MAX_LENGTH: Final = 64


class AwardKind(StrEnum):
    """The award vocabulary a festival starts with.

    Not a closed set any more, and not what a row is typed as: a row stores a code
    string, and a festival's own scale decides which codes exist and what they read as.
    What this enum is for is twofold - it seeds every new festival's scale, so nobody
    has to type nine степени before running a protocol, and it names the codes protocols
    were storing before scales were configurable, so those rows keep rendering exactly
    as they did.

    Order of declaration is the **order of seniority**, from Гран-при down to the
    participation diploma. That is what :data:`AWARD_ORDER` reads, and it is the only
    ranking this context has: within one kind nothing is ranked at all.
    """

    GRAND_PRIX = "GRAND_PRIX"
    GRAND_PRIX_NOMINEE = "GRAND_PRIX_NOMINEE"
    LAUREATE_I = "LAUREATE_I"
    LAUREATE_II = "LAUREATE_II"
    LAUREATE_III = "LAUREATE_III"
    DIPLOMANT_I = "DIPLOMANT_I"
    DIPLOMANT_II = "DIPLOMANT_II"
    DIPLOMANT_III = "DIPLOMANT_III"
    PARTICIPANT = "PARTICIPANT"

    @property
    def label(self) -> str:
        """How this award is written out, on a protocol and on a diploma alike."""
        return AWARD_LABELS[self]

    @property
    def seniority(self) -> int:
        """Rank among the kinds (0 = Гран-при). Not a place - see the class docstring."""
        return AWARD_ORDER[self]


#: The wording each award is printed with. Kept beside the enum so the organizer's
#: table, the published protocol and the diploma's ``award.degree`` all name an award
#: identically - Russian is the platform's language (ARCH-001), so these are the
#: values themselves and not a translation layer.
AWARD_LABELS: Final[dict[AwardKind, str]] = {
    AwardKind.GRAND_PRIX: "Гран-при",
    AwardKind.GRAND_PRIX_NOMINEE: "Номинант на Гран-при",
    AwardKind.LAUREATE_I: "Лауреат I степени",
    AwardKind.LAUREATE_II: "Лауреат II степени",
    AwardKind.LAUREATE_III: "Лауреат III степени",
    AwardKind.DIPLOMANT_I: "Дипломант I степени",
    AwardKind.DIPLOMANT_II: "Дипломант II степени",
    AwardKind.DIPLOMANT_III: "Дипломант III степени",
    AwardKind.PARTICIPANT: "Диплом участника",
}

#: Award → its rank among the kinds, derived from declaration order so the two can
#: never drift apart. Used to group a protocol by award, never to place acts.
AWARD_ORDER: Final[dict[AwardKind, int]] = {kind: index for index, kind in enumerate(AwardKind)}


class ProtocolStatus(StrEnum):
    """Whether the results have left the organizer's screen.

    ``DRAFT`` is the jury's working table: awards go in, get changed, get cleared, and
    nobody outside the organization sees any of it. ``PUBLISHED`` is the moment the
    results became a fact - a public link resolves, diplomas carry their degree, and
    the participants have been told.

    A published protocol is still **editable**: results do get corrected, and a
    platform that made that impossible would be worked around with a second protocol.
    What publication changes is that every further edit has to be published again to
    reach anyone, and doing so raises the protocol's revision - so a correction is a
    deliberate act with a number on it rather than a silent rewrite.
    """

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class ProtocolColumn(StrEnum):
    """A column of the protocol table.

    A protocol *is* a table - one row per act, in the order they performed - and these
    are the columns it can carry. They are also the unit the published version is cut
    along: an organizer chooses which of these the public page shows, because a
    protocol that lists a child's school and teacher to the whole internet is a
    different document from one that lists the award.

    Order here is the canonical render order, whichever subset was chosen, so a column
    sits in the same place on the organizer's screen and on the public page.
    """

    POSITION = "POSITION"
    PARTICIPANT = "PARTICIPANT"
    TITLE = "TITLE"
    AWARD = "AWARD"
    NOMINATION = "NOMINATION"
    DISCIPLINE = "DISCIPLINE"
    PARTICIPANT_GROUP = "PARTICIPANT_GROUP"
    AGE_CATEGORY = "AGE_CATEGORY"
    PARTICIPATION_FORMAT = "PARTICIPATION_FORMAT"
    TEACHERS = "TEACHERS"
    ORGANIZATION = "ORGANIZATION"


#: The header each column is printed under.
#: **Display vocabulary.** The code's ``NOMINATION`` is shown to people as «Жанр», and
#: ``DISCIPLINE`` as «Номинация». The identifiers keep the older names on purpose — they
#: run through the API contract, the stored protocol snapshots and every client — while
#: the words the platform speaks to organizers and participants changed. This mapping is
#: the whole of that shift; nothing else needs to know about it.
COLUMN_LABELS: Final[dict[ProtocolColumn, str]] = {
    ProtocolColumn.POSITION: "№",
    ProtocolColumn.PARTICIPANT: "Участник",
    ProtocolColumn.TITLE: "Номер",
    ProtocolColumn.AWARD: "Результат",
    ProtocolColumn.NOMINATION: "Жанр",
    ProtocolColumn.DISCIPLINE: "Номинация",
    ProtocolColumn.PARTICIPANT_GROUP: "Состав участников",
    ProtocolColumn.AGE_CATEGORY: "Возрастная категория",
    ProtocolColumn.PARTICIPATION_FORMAT: "Формат участия",
    ProtocolColumn.TEACHERS: "Педагог",
    ProtocolColumn.ORGANIZATION: "Организация",
}

#: What a published protocol shows when the organizer chose nothing in particular.
#: Deliberately the four columns a result is unambiguous with and no more: a public
#: protocol must never widen by accident, so "nothing chosen" is a narrow default
#: rather than every column the table happens to have.
DEFAULT_PUBLIC_COLUMNS: Final[tuple[ProtocolColumn, ...]] = (
    ProtocolColumn.POSITION,
    ProtocolColumn.PARTICIPANT,
    ProtocolColumn.TITLE,
    ProtocolColumn.AWARD,
)


def parse_award(raw: object) -> AwardCode | None:
    """Read an award code from the wire. ``None`` or blank means "not decided yet".

    Clearing a result is a legitimate edit - a row entered by mistake, an act
    withdrawn between the performance and the protocol - so an empty value is a value
    here and not a validation failure.

    Only the *shape* is checked here, not membership: whether a code exists is a
    question about the festival's scale, which is another context's, and a protocol
    that refused a code the organizer had just added would be checking it in the wrong
    place. What this guards against is a free-text degree arriving as an award and
    becoming the string a diploma is printed from.
    """
    if raw is None:
        return None
    text = str(raw).strip().upper()
    if not text:
        return None
    if not _AWARD_CODE_RE.match(text):
        raise InvalidProtocolDataError("Неизвестная награда.")
    return text


def default_award_label(code: str) -> str | None:
    """The built-in name for ``code``, or ``None`` if it is not one of the defaults."""
    try:
        return AWARD_LABELS[AwardKind(str(code).strip().upper())]
    except (ValueError, KeyError):
        return None


def parse_columns(values: Iterable[object] | None) -> tuple[ProtocolColumn, ...]:
    """Read a selection of columns, in canonical order and without duplicates.

    An empty selection is returned empty; deciding that "nothing chosen" means
    :data:`DEFAULT_PUBLIC_COLUMNS` is the aggregate's business, not the parser's.
    """
    if values is None:
        return ()
    if isinstance(values, str):
        raise InvalidProtocolDataError("Columns must be a list of column names.")
    chosen: set[ProtocolColumn] = set()
    for raw in values:
        try:
            chosen.add(ProtocolColumn(str(raw).upper()))
        except ValueError as exc:
            raise InvalidProtocolDataError("Неизвестная колонка протокола.") from exc
    return tuple(column for column in ProtocolColumn if column in chosen)


@dataclass(frozen=True, slots=True)
class PublishedResult:
    """One line of the protocol **as it was published**: the act, its number, its award.

    Deliberately three values and no names. What gets frozen at publication is the
    *decision* - which acts, in what order, with what result - because that is what the
    revision number is about and what must not change until somebody publishes again.

    The performer's name, the act's title and the teacher are **not** frozen: they are read
    live from Applications every time the page renders, so a misspelled child's surname is
    fixed by correcting the entry and not by republishing a nomination's results. The split
    is the whole point of this type - a diploma freezes everything because it is a document
    that was handed over, and a protocol freezes only the verdict because it is a page.
    """

    submission_id: uuid.UUID
    number: int
    award: AwardCode | None = None

    def to_dict(self) -> dict[str, object]:
        """The JSON shape the snapshot column stores this line as."""
        return {
            "submission_id": str(self.submission_id),
            "number": self.number,
            "award": self.award,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> PublishedResult:
        """Read one line back. A blank award is a published blank, not a missing value."""
        award = data.get("award")
        return cls(
            submission_id=uuid.UUID(str(data["submission_id"])),
            number=int(str(data.get("number") or 0)),
            # Read without validating: a snapshot outlives the scale it was published
            # under, and a published page must not go missing because a tier was renamed.
            award=str(award).strip().upper() or None if award else None,
        )


@dataclass(frozen=True, slots=True)
class PublishedSnapshot:
    """The revision of a protocol that is currently public.

    Everything the public page is rendered from except the live names: the heading it was
    published under, the columns it was cut to, and the results themselves. Held as one
    immutable value so "what is public" is a thing the aggregate *has* rather than something
    inferred from its current state - which is what lets a jury correct a result after the
    ceremony without the correction appearing before anyone chose to publish it.
    """

    name: str
    columns: tuple[ProtocolColumn, ...]
    results: tuple[PublishedResult, ...]

    def to_dict(self) -> dict[str, object]:
        """The JSON shape the snapshot column stores."""
        return {
            "name": self.name,
            "columns": [column.value for column in self.columns],
            "results": [result.to_dict() for result in self.results],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> PublishedSnapshot:
        """Read a stored snapshot back.

        Tolerant of a document written before a field existed - a snapshot outlives the code
        that wrote it, and a published protocol that failed to load would be a page gone
        missing rather than an error anybody could act on.
        """
        raw_columns = data.get("columns")
        raw_results = data.get("results")
        return cls(
            name=str(data.get("name") or ""),
            columns=parse_columns(raw_columns if isinstance(raw_columns, list) else []),
            results=tuple(
                PublishedResult.from_dict(entry) for entry in (raw_results if isinstance(raw_results, list) else []) if isinstance(entry, Mapping)
            ),
        )


@dataclass(frozen=True, slots=True)
class ProtocolName:
    """A non-empty, length-bounded protocol name ("Вокал, итоги")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProtocolDataError("Укажите название протокола.")
        if len(stripped) > _NAME_MAX:
            raise InvalidProtocolDataError(f"Название протокола — не длиннее {_NAME_MAX} символов.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PublicSlug:
    """The token in a published protocol's URL (``/protocol/AbX82K``).

    Unlike a programme's link this one is *meant* to be found - it is linked from the
    competition's landing page under "Результаты". The unguessable alphabet is kept
    anyway, because the slug is minted at publication and a guessable one would let
    the results be read off the URL space before the ceremony announced them.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not (_SLUG_MIN_LENGTH <= len(stripped) <= _SLUG_MAX_LENGTH):
            raise InvalidProtocolDataError(f"Адрес ссылки — от {_SLUG_MIN_LENGTH} до {_SLUG_MAX_LENGTH} символов.")
        if any(char not in _SLUG_ALPHABET for char in stripped):
            raise InvalidProtocolDataError("В адресе ссылки допустимы только однозначные латинские символы и цифры.")
        object.__setattr__(self, "value", stripped)

    @classmethod
    def generate(cls) -> PublicSlug:
        """Mint a fresh random slug (~57 bits of entropy at the default length)."""
        return cls("".join(secrets.choice(_SLUG_ALPHABET) for _ in range(_SLUG_LENGTH)))

    def __str__(self) -> str:
        return self.value
