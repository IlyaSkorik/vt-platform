"""Value objects for the Programs bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

Identifiers are plain :class:`uuid.UUID` values rather than one wrapper class per
reference (the approach the Diplomas context takes): this context holds ids only -
its own, and ``competition_id`` / ``nomination_id`` / ``submission_id`` pointing at
other contexts - and none of them carry behaviour worth a type of their own. The
value objects here are the ones with actual rules: a program's name, an item's
title, the two kinds of duration, the item kind, and a public slug.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .exceptions import InvalidProgramDataError

__all__ = [
    "BREAK_AFTER_ITEMS_MAX",
    "BUFFER_MAX_SECONDS",
    "CELL_VALUE_MAX",
    "COLUMN_LABELS",
    "CUSTOM_COLUMN_PREFIX",
    "DEFAULT_AWARD_SECONDS",
    "DEFAULT_AWARD_TITLE",
    "DEFAULT_BREAK_SECONDS",
    "DEFAULT_BREAK_TITLE",
    "DEFAULT_GROUPING",
    "DEFAULT_OPENING_SECONDS",
    "DEFAULT_OPENING_TITLE",
    "DEFAULT_PUBLIC_COLUMNS",
    "DURATION_MAX_SECONDS",
    "REPEAT_GAP_MAX",
    "ArrangementBlock",
    "ArrangementSettings",
    "BreakRule",
    "CellValue",
    "ColumnRef",
    "ColumnTitle",
    "GroupingAxis",
    "ItemDuration",
    "ItemTitle",
    "PerformanceOrder",
    "ProgramColumn",
    "ProgramItemKind",
    "ProgramItemProgress",
    "ProgramName",
    "PublicSlug",
    "ShareName",
    "TimeBuffer",
    "parse_column_refs",
    "parse_columns",
]

_NAME_MAX: Final = 200
_TITLE_MAX: Final = 200
_COLUMN_TITLE_MAX: Final = 120

#: A hand-filled cell is a note, not a document: long enough for "фонограмма на флешке
#: у звукорежиссёра", short enough that a table stays a table.
CELL_VALUE_MAX: Final = 500

#: How a custom column is named on the wire, distinguishing it from the built-in keys.
CUSTOM_COLUMN_PREFIX: Final = "custom:"

#: A single item may not be longer than a day - the sanity ceiling a real running
#: order can never legitimately cross.
DURATION_MAX_SECONDS: Final = 24 * 60 * 60

#: The buffer pads one performance slot; anything beyond an hour is a break, and a
#: break is an item of its own.
BUFFER_MAX_SECONDS: Final = 60 * 60

_SLUG_ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_SLUG_LENGTH: Final = 10
_SLUG_MIN_LENGTH: Final = 6
_SLUG_MAX_LENGTH: Final = 64


class ProgramColumn(StrEnum):
    """A column of the programme table.

    A programme *is* a table: one row per item, and these are the columns it can carry.
    They are also the unit a public link is cut along - publishing an edition means
    choosing which of these the reader sees, so the sound engineer gets the time, the
    act and its notes while the audience screen gets the time, the participant and the
    act and nothing else.

    Order here is the canonical order a table is rendered in, whichever subset was
    chosen: a column means the same thing and sits in the same place on every screen.
    """

    POSITION = "POSITION"
    TIME = "TIME"
    PARTICIPANT = "PARTICIPANT"
    TITLE = "TITLE"
    DURATION = "DURATION"
    NOMINATION = "NOMINATION"
    DISCIPLINE = "DISCIPLINE"
    PARTICIPANT_GROUP = "PARTICIPANT_GROUP"
    PARTICIPANT_COUNT = "PARTICIPANT_COUNT"
    AGE_CATEGORY = "AGE_CATEGORY"
    PARTICIPATION_FORMAT = "PARTICIPATION_FORMAT"
    TEACHERS = "TEACHERS"
    ORGANIZATION = "ORGANIZATION"
    CONTACTS = "CONTACTS"
    COMMENT = "COMMENT"


#: The header each column is printed under. Kept beside the enum so the organizer's
#: table and every published edition name a column identically - Russian is the
#: platform's language (ARCH-001), so these are the values, not a translation layer.
#: **Display vocabulary.** The code's ``NOMINATION`` is shown to people as «Жанр», and
#: ``DISCIPLINE`` as «Номинация». The identifiers keep the older names on purpose — they
#: run through the API contract, the stored protocol snapshots and every client — while
#: the words the platform speaks to organizers and participants changed. This mapping is
#: the whole of that shift; nothing else needs to know about it.
COLUMN_LABELS: Final[dict[ProgramColumn, str]] = {
    ProgramColumn.POSITION: "№",
    ProgramColumn.TIME: "Время",
    ProgramColumn.PARTICIPANT: "Участник",
    ProgramColumn.TITLE: "Номер",
    ProgramColumn.DURATION: "Длительность",
    ProgramColumn.NOMINATION: "Жанр",
    ProgramColumn.DISCIPLINE: "Номинация",
    ProgramColumn.PARTICIPANT_GROUP: "Состав участников",
    # «Человек», not «Участников»: it stands next to «Состав участников» in the same
    # table, and two headers one word apart are two headers nobody can tell apart at a
    # glance. It is also four characters shorter, which a column this narrow notices.
    ProgramColumn.PARTICIPANT_COUNT: "Человек",
    ProgramColumn.AGE_CATEGORY: "Возрастная категория",
    ProgramColumn.PARTICIPATION_FORMAT: "Формат участия",
    ProgramColumn.TEACHERS: "Педагог",
    ProgramColumn.ORGANIZATION: "Организация",
    ProgramColumn.CONTACTS: "Контакты",
    ProgramColumn.COMMENT: "Комментарий",
}

#: What a published edition shows when the organizer chose nothing in particular - the
#: four columns every reader of a programme needs before any other.
DEFAULT_PUBLIC_COLUMNS: Final[tuple[ProgramColumn, ...]] = (
    ProgramColumn.POSITION,
    ProgramColumn.TIME,
    ProgramColumn.PARTICIPANT,
    ProgramColumn.TITLE,
)


@dataclass(frozen=True, slots=True)
class ColumnRef:
    """A reference to one column of the table: a built-in one, or a custom one by id.

    Custom columns are the escape hatch for whatever a particular festival needs and the
    built-in vocabulary does not have - "микрофон", "реквизит на сцене", "оплачено". They
    are named by the organizer and filled in by hand, and they behave like any other
    column everywhere else: they can be published on a link and they render into a cell.

    On the wire a built-in is its own name (``TIME``) and a custom one is
    ``custom:<uuid>``, so one list can carry both without a second field to disambiguate.
    """

    builtin: ProgramColumn | None = None
    custom_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if (self.builtin is None) == (self.custom_id is None):
            raise InvalidProgramDataError("Колонка задана неверно: выберите либо встроенную, либо свою.")

    @classmethod
    def of(cls, column: ProgramColumn) -> ColumnRef:
        """Reference a built-in column."""
        return cls(builtin=column)

    @classmethod
    def custom(cls, column_id: uuid.UUID) -> ColumnRef:
        """Reference a custom column by id."""
        return cls(custom_id=column_id)

    @classmethod
    def parse(cls, raw: object) -> ColumnRef:
        """Read a wire key: ``"TIME"`` or ``"custom:<uuid>"``."""
        text = str(raw).strip()
        if text.lower().startswith(CUSTOM_COLUMN_PREFIX):
            try:
                return cls.custom(uuid.UUID(text[len(CUSTOM_COLUMN_PREFIX) :]))
            except ValueError as exc:
                raise InvalidProgramDataError("Неверная ссылка на свою колонку.") from exc
        try:
            return cls.of(ProgramColumn(text.upper()))
        except ValueError as exc:
            raise InvalidProgramDataError("Неизвестная колонка программы.") from exc

    @property
    def is_custom(self) -> bool:
        return self.custom_id is not None

    @property
    def key(self) -> str:
        """The wire key for this column."""
        if self.custom_id is not None:
            return f"{CUSTOM_COLUMN_PREFIX}{self.custom_id}"
        # __post_init__ guarantees exactly one of the two is set.
        return self.builtin.value if self.builtin is not None else ""

    def __str__(self) -> str:
        return self.key


@dataclass(frozen=True, slots=True)
class ColumnTitle:
    """The header of a custom column ("Микрофон", "Реквизит")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Укажите название колонки.")
        if len(stripped) > _COLUMN_TITLE_MAX:
            raise InvalidProgramDataError(f"Название колонки — не длиннее {_COLUMN_TITLE_MAX} символов.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CellValue:
    """A hand-filled value in a custom column. Blank means "nothing here"."""

    value: str = ""

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if len(stripped) > CELL_VALUE_MAX:
            raise InvalidProgramDataError(f"Значение в ячейке — не длиннее {CELL_VALUE_MAX} символов.")
        object.__setattr__(self, "value", stripped)

    @property
    def is_blank(self) -> bool:
        return not self.value

    def __str__(self) -> str:
        return self.value


class ProgramItemProgress(StrEnum):
    """How far one slot has got on the day itself.

    The host drives this from their own link, and every screen reading the programme sees
    it: ``ON_STAGE`` is what a display beside the stage highlights, ``PERFORMED`` is what
    it greys out, and ``SKIPPED`` is the act that did not appear.
    """

    PENDING = "PENDING"
    ON_STAGE = "ON_STAGE"
    PERFORMED = "PERFORMED"
    SKIPPED = "SKIPPED"

    @property
    def is_finished(self) -> bool:
        """Whether this slot is behind us, one way or the other."""
        return self in {ProgramItemProgress.PERFORMED, ProgramItemProgress.SKIPPED}


def parse_column_refs(values: Iterable[object] | None) -> tuple[ColumnRef, ...]:
    """Read a selection of columns (built-in or custom), without duplicates.

    Order is preserved as sent; the aggregate normalizes it against its own custom
    columns, which is the only place that knows their order.
    """
    if values is None:
        return ()
    if isinstance(values, str):
        raise InvalidProgramDataError("Columns must be a list of column names.")
    refs: list[ColumnRef] = []
    for raw in values:
        ref = ColumnRef.parse(raw)
        if ref not in refs:
            refs.append(ref)
    return tuple(refs)


def parse_columns(values: Iterable[object] | None) -> tuple[ProgramColumn, ...]:
    """Read a selection of columns, in canonical order and without duplicates.

    An empty selection is returned empty; it is the caller's business to decide that
    "nothing chosen" means :data:`DEFAULT_PUBLIC_COLUMNS`.
    """
    if values is None:
        return ()
    if isinstance(values, str):
        raise InvalidProgramDataError("Columns must be a list of column names.")
    chosen: set[ProgramColumn] = set()
    for raw in values:
        try:
            chosen.add(ProgramColumn(str(raw).upper()))
        except ValueError as exc:
            raise InvalidProgramDataError("Неизвестная колонка программы.") from exc
    return tuple(column for column in ProgramColumn if column in chosen)


class ProgramItemKind(StrEnum):
    """What a slot in the running order *is*.

    ``PERFORMANCE`` binds one competing act (a submission) and takes its length
    from it. Every other kind is a **standalone block**: it carries its own title
    and its own duration, and nothing outside this context needs to exist for it.

    ``BREAK`` is what the interface offers today ("Перерыв", "Обед", "Подготовка
    сцены"). ``OPENING``, ``AWARD``, ``MASTER_CLASS`` and ``TECHNICAL`` are already
    valid and already schedule correctly - they are the same shape, and listing them
    here is the point of the design: a new kind of block needs no new table, no
    migration and no change to the time calculation.
    """

    PERFORMANCE = "PERFORMANCE"
    BREAK = "BREAK"
    OPENING = "OPENING"
    AWARD = "AWARD"
    MASTER_CLASS = "MASTER_CLASS"
    TECHNICAL = "TECHNICAL"

    @property
    def binds_performance(self) -> bool:
        """Whether this kind references a competing act instead of carrying a title."""
        return self is ProgramItemKind.PERFORMANCE

    @property
    def takes_number(self) -> bool:
        """Whether this kind of slot is numbered at all.

        Only performances. A number is what a participant is told and what the sound desk
        cues from, and a break has neither - numbering it pushes every act after it one
        place along and makes "номер 12" mean a fifteen-minute gap. The running order still
        contains the block, it simply has no «№».
        """
        return self is ProgramItemKind.PERFORMANCE

    @property
    def takes_buffer(self) -> bool:
        """Whether the program's buffer pads this kind of slot.

        Only performances: the buffer exists to absorb applause, stage entry and
        exit between acts. A break already *is* slack, and padding it would silently
        stretch the very item the organizer sized by hand.
        """
        return self is ProgramItemKind.PERFORMANCE


@dataclass(frozen=True, slots=True)
class ProgramName:
    """A non-empty, length-bounded program name ("Вокал, 1 отделение")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Укажите название программы.")
        if len(stripped) > _NAME_MAX:
            raise InvalidProgramDataError(f"Название программы — не длиннее {_NAME_MAX} символов.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ShareName:
    """A non-empty, length-bounded name for a public share ("Программа звукорежиссёра")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Укажите название публичной программы.")
        if len(stripped) > _NAME_MAX:
            raise InvalidProgramDataError(f"Название публичной программы — не длиннее {_NAME_MAX} символов.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ItemTitle:
    """A non-empty, length-bounded title for a standalone block ("Обед")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Укажите название строки программы.")
        if len(stripped) > _TITLE_MAX:
            raise InvalidProgramDataError(f"Название строки — не длиннее {_TITLE_MAX} символов.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ItemDuration:
    """How long a slot lasts, as a whole number of seconds.

    Stored as an :class:`int` (never a float) so accumulated schedules stay exact.
    Strictly positive: a slot of no length would occupy a position in the running
    order while moving no clock.
    """

    seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, int) or isinstance(self.seconds, bool):
            raise InvalidProgramDataError(f"Duration seconds must be an int, got {type(self.seconds)!r}.")
        if self.seconds <= 0:
            raise InvalidProgramDataError("Длительность должна быть больше нуля.")
        if self.seconds > DURATION_MAX_SECONDS:
            raise InvalidProgramDataError(f"Длительность — не больше {DURATION_MAX_SECONDS // 60} минут.")

    @classmethod
    def of(cls, *, minutes: int = 0, seconds: int = 0) -> ItemDuration:
        """Build a duration from minutes and/or seconds."""
        return cls(seconds=minutes * 60 + seconds)

    def __str__(self) -> str:
        minutes, seconds = divmod(self.seconds, 60)
        return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True, slots=True)
class TimeBuffer:
    """The padding added to every performance slot when the schedule is computed.

    A program-level setting (30 seconds, 45 seconds, a minute, ...) that **never
    changes an act's own duration** - it only widens the slot the act sits in, so
    the same act keeps its declared length everywhere else in the platform.
    """

    seconds: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, int) or isinstance(self.seconds, bool):
            raise InvalidProgramDataError(f"Buffer seconds must be an int, got {type(self.seconds)!r}.")
        if self.seconds < 0:
            raise InvalidProgramDataError("Перерыв не может быть отрицательным.")
        if self.seconds > BUFFER_MAX_SECONDS:
            raise InvalidProgramDataError(f"Перерыв — не больше {BUFFER_MAX_SECONDS // 60} минут.")

    @classmethod
    def none(cls) -> TimeBuffer:
        """No padding at all."""
        return cls(seconds=0)

    def __str__(self) -> str:
        minutes, seconds = divmod(self.seconds, 60)
        return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True, slots=True)
class PublicSlug:
    """The unguessable token in a public program URL (``/program/AbX82K``).

    The slug *is* the credential: a public program carries no authentication, so it
    is minted from a confusable-free alphabet with enough entropy that a link cannot
    be found by trying. Case-sensitive, and never derived from the program's name.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not (_SLUG_MIN_LENGTH <= len(stripped) <= _SLUG_MAX_LENGTH):
            raise InvalidProgramDataError(f"Адрес ссылки — от {_SLUG_MIN_LENGTH} до {_SLUG_MAX_LENGTH} символов.")
        if any(char not in _SLUG_ALPHABET for char in stripped):
            raise InvalidProgramDataError("В адресе ссылки допустимы только однозначные латинские символы и цифры.")
        object.__setattr__(self, "value", stripped)

    @classmethod
    def generate(cls) -> PublicSlug:
        """Mint a fresh random slug (~57 bits of entropy at the default length)."""
        return cls("".join(secrets.choice(_SLUG_ALPHABET) for _ in range(_SLUG_LENGTH)))

    def __str__(self) -> str:
        return self.value


class GroupingAxis(StrEnum):
    """An axis a generated running order may be grouped along.

    These are the facets a festival day is actually blocked out by: the audience sees
    all of «Эстрадный вокал» together, and within it all of «7-9 лет» together. The
    organizer picks the order of the axes, and that order *is* the shape of the day -
    grouping by age then nomination builds a different festival from the reverse.

    Every axis is a facet the Applications context already carries on an entry, so
    grouping needs no new data from anybody: see
    :class:`~apps.programs.application.interfaces.CatalogPerformance`.
    """

    NOMINATION = "NOMINATION"
    DISCIPLINE = "DISCIPLINE"
    AGE_CATEGORY = "AGE_CATEGORY"
    PARTICIPANT_GROUP = "PARTICIPANT_GROUP"
    PARTICIPATION_FORMAT = "PARTICIPATION_FORMAT"
    ORGANIZATION = "ORGANIZATION"


class PerformanceOrder(StrEnum):
    """How acts are ordered *inside* one group.

    Grouping decides which acts stand together; this decides who opens the group. The
    choice is a stage decision, not a data one - "младшие вперёд" warms a hall up,
    "короткие вперёд" keeps the first half moving, and alphabetical is what a jury
    chairman asks for when nobody wants to be seen choosing.
    """

    AGE_ASC = "AGE_ASC"
    AGE_DESC = "AGE_DESC"
    TITLE = "TITLE"
    PARTICIPANT = "PARTICIPANT"
    ORGANIZATION = "ORGANIZATION"
    DURATION_ASC = "DURATION_ASC"
    DURATION_DESC = "DURATION_DESC"


class BreakRule(StrEnum):
    """When the generator puts a break into the running order.

    One rule, not a set of them, because breaks that fire on two triggers at once are
    the thing nobody can predict from the settings screen. An отделение is simply what
    lies between two breaks, so "перерыв каждые 90 минут" and "отделение не длиннее
    90 минут" are the same instruction said twice - and only said once here.
    """

    #: No breaks at all: a short nomination runs straight through.
    NONE = "NONE"
    #: A break once the acts since the last one would pass ``break_after_seconds``.
    EVERY_DURATION = "EVERY_DURATION"
    #: A break after every ``break_after_items`` acts.
    EVERY_COUNT = "EVERY_COUNT"
    #: A break wherever the *first* grouping axis changes value.
    BETWEEN_GROUPS = "BETWEEN_GROUPS"


#: What a generated program groups by when the organizer states nothing: the three
#: axes every festival programme is read along.
DEFAULT_GROUPING: Final[tuple[GroupingAxis, ...]] = (
    GroupingAxis.NOMINATION,
    GroupingAxis.DISCIPLINE,
    GroupingAxis.AGE_CATEGORY,
)

#: The ceiling on that gap. Beyond this the constraint stops being "дайте
#: переодеться" and starts rewriting the running order around one participant.
REPEAT_GAP_MAX: Final = 20

#: The most acts a single generated отделение may hold before a break is forced in.
BREAK_AFTER_ITEMS_MAX: Final = 500

#: What a generated service block is called and how long it lasts when the organizer
#: turned it on but did not bother to name it. Festival vocabulary, so the common case
#: is one checkbox rather than a title and a duration typed out every time.
DEFAULT_BREAK_TITLE: Final = "Перерыв"
DEFAULT_BREAK_SECONDS: Final = 10 * 60
DEFAULT_OPENING_TITLE: Final = "Открытие"
DEFAULT_OPENING_SECONDS: Final = 15 * 60
DEFAULT_AWARD_TITLE: Final = "Награждение"
DEFAULT_AWARD_SECONDS: Final = 30 * 60


@dataclass(frozen=True, slots=True)
class ArrangementBlock:
    """A service block the generator inserts on its own (a break, an opening, an award).

    Title and length only: which *kind* of block it becomes is decided by where the
    generator puts it, not by the setting.
    """

    title: ItemTitle
    duration: ItemDuration

    @classmethod
    def of(cls, title: str, *, seconds: int) -> ArrangementBlock:
        """Build a block from the raw title and length a settings form sends."""
        return cls(title=ItemTitle(title), duration=ItemDuration(seconds))


@dataclass(frozen=True, slots=True)
class ArrangementSettings:
    """The rules one generated programme was built from.

    Kept on the aggregate rather than passed and forgotten, because a running order is
    regenerated far more often than it is first built: entries keep arriving until the
    day before, and "пересобрать по тем же правилам" has to be one button rather than
    a settings form refilled from memory.

    The defaults are a working festival programme on their own - grouped the way a
    programme is read, youngest first, no breaks and no service blocks - so a client
    may send nothing at all and still get something usable.
    """

    grouping: tuple[GroupingAxis, ...] = DEFAULT_GROUPING
    order_within_group: PerformanceOrder = PerformanceOrder.AGE_ASC
    break_rule: BreakRule = BreakRule.NONE
    #: The length of acts after which ``EVERY_DURATION`` fires. Ignored by other rules.
    break_after_seconds: int = 0
    #: The number of acts after which ``EVERY_COUNT`` fires. Ignored by other rules.
    break_after_items: int = 0
    #: The break itself. Required by every rule but ``NONE``.
    break_block: ArrangementBlock | None = None
    #: How many slots must separate two acts of the same participant; 0 turns it off.
    #: Deliberately about *participants* only - a studio brings twenty acts and a
    #: teacher a dozen, so spacing those apart would be spacing out the whole day.
    repeat_gap: int = 0
    #: An opening block at the very top of the day, if the festival has one.
    opens_with: ArrangementBlock | None = None
    #: An award ceremony at the very bottom, if the festival hands out diplomas on stage.
    closes_with: ArrangementBlock | None = None

    def __post_init__(self) -> None:
        if len(set(self.grouping)) != len(self.grouping):
            raise InvalidProgramDataError("Каждый признак группировки можно выбрать только один раз.")
        if not isinstance(self.repeat_gap, int) or isinstance(self.repeat_gap, bool) or self.repeat_gap < 0:
            raise InvalidProgramDataError("Интервал между номерами одного участника не может быть отрицательным.")
        if self.repeat_gap > REPEAT_GAP_MAX:
            raise InvalidProgramDataError(f"Интервал между номерами одного участника — не больше {REPEAT_GAP_MAX}.")
        if self.break_rule is not BreakRule.NONE and self.break_block is None:
            raise InvalidProgramDataError("Укажите название и длительность перерыва.")
        if self.break_rule is BreakRule.EVERY_DURATION and self.break_after_seconds <= 0:
            raise InvalidProgramDataError("Укажите, через сколько минут ставить перерыв.")
        if self.break_rule is BreakRule.EVERY_DURATION and self.break_after_seconds > DURATION_MAX_SECONDS:
            raise InvalidProgramDataError(f"Отделение — не длиннее {DURATION_MAX_SECONDS // 3600} часов.")
        if self.break_rule is BreakRule.EVERY_COUNT and not 0 < self.break_after_items <= BREAK_AFTER_ITEMS_MAX:
            raise InvalidProgramDataError(f"Укажите, через сколько номеров ставить перерыв (до {BREAK_AFTER_ITEMS_MAX}).")
