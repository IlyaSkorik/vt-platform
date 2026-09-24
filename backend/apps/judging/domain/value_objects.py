"""Value objects for the Judging bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

Three of them carry the whole configuration an organizer fills in, and they are worth
introducing together because they only make sense as a chain:

* :class:`Criterion` — what a judge is asked about, out of how many points, and how
  much that answer weighs. Criteria are grouped into a :class:`CriteriaSet` scoped to
  a genre or, when a genre is not uniform enough, to one nomination inside it.
* :class:`ScoringRules` — how several judges' marks become one number for an act.
* :class:`AwardScale` — how that number becomes a result with a name on it. This is
  the part festivals disagree about most: one organizer hands out "1 место", another
  "Лауреат I степени" and a "Гран-при", and neither vocabulary is more correct. So
  the scale is a list the organizer writes, not an enum this codebase picked, and a
  tier is matched by the band of points it covers.

Scores are :class:`~decimal.Decimal` throughout. A jury's arithmetic is read off a
screen in a hall and copied onto a diploma, and binary floating point turns 9.1 + 9.2
into a number that does not print the way anyone typed it.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Final

from .exceptions import InvalidJudgingDataError

__all__ = [
    "DEFAULT_AWARD_TIERS",
    "AggregationMethod",
    "AwardScale",
    "AwardTier",
    "BoardReveal",
    "BoardSettings",
    "BoardVisibility",
    "CriteriaScope",
    "CriteriaSet",
    "Criterion",
    "JuryMemberStatus",
    "PerformanceScoringStatus",
    "Score",
    "ScoringRules",
    "TallyDimension",
    "TallyScope",
    "parse_dimensions",
    "parse_score",
]

#: Two decimal places is what a criterion sheet is ever written to, and it is also the
#: most a hall screen can show without the number turning into noise.
_SCORE_EXPONENT: Final = Decimal("0.01")

#: A ceiling high enough for any sane criteria set (twenty criteria out of fifty
#: points each, summed across a dozen judges) and low enough that a typo in a
#: hand-entered maximum is caught rather than stored.
_SCORE_MAX: Final = Decimal("100000")

_TIER_CODE_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_LABEL_MAX: Final = 120
_NAME_MAX: Final = 200


def parse_score(value: object, *, what: str) -> Decimal:
    """Read a score off the wire, or raise :class:`InvalidJudgingDataError`.

    Accepts the shapes JSON actually delivers — a number, a numeric string — and
    refuses the ones that would quietly become garbage: ``NaN``, infinities, and
    anything negative. Quantized to two places on the way in, so a stored score and a
    computed one compare equal instead of differing in the fifteenth digit.
    """
    try:
        score = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InvalidJudgingDataError(f"{what} — укажите число.") from exc
    if not score.is_finite():
        raise InvalidJudgingDataError(f"{what} — укажите число.")
    if score < 0:
        raise InvalidJudgingDataError(f"{what} не может быть отрицательным.")
    if score > _SCORE_MAX:
        raise InvalidJudgingDataError(f"{what} — слишком большое число.")
    return score.quantize(_SCORE_EXPONENT)


#: The type every point value in this context is held as. Named so signatures read as
#: what they mean rather than as "another Decimal".
Score = Decimal


def _text(value: object, *, what: str, limit: int) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise InvalidJudgingDataError(f"Укажите {what}.")
    if len(raw) > limit:
        raise InvalidJudgingDataError(f"{what.capitalize()} — не длиннее {limit} символов.")
    return raw


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------


class CriteriaScope(StrEnum):
    """What a set of criteria applies to.

    ``CATEGORY`` is a genre's set and the one organizers fill in. ``DISCIPLINE`` is the
    exception a genre sometimes needs: "вокал" judges intonation, but the "эстрадный
    вокал" nomination inside it is also judged on stage presence, and forcing the genre
    to carry a criterion half its nominations ignore is how a criteria sheet stops
    being read.

    A discipline's set **replaces** its genre's rather than adding to it. Merging two
    lists would leave an organizer unable to drop an inherited criterion, and a judge
    unable to tell which sheet they are on.
    """

    CATEGORY = "CATEGORY"
    DISCIPLINE = "DISCIPLINE"


@dataclass(frozen=True, slots=True)
class Criterion:
    """One line on a judge's sheet.

    :attr:`max_score` is what a judge may give at most, and :attr:`weight` is how much
    that counts toward the act's total. Two knobs rather than one because they answer
    different questions: a festival marks everything out of 10 because that is what a
    jury is used to, and *then* decides technique matters twice as much as costume.

    A criterion keeps its :attr:`id` for life. Scores point at it, so renaming
    "Техника" to "Техника исполнения" must not orphan a mark already given.
    """

    id: uuid.UUID
    name: str
    max_score: Score
    weight: Decimal
    sort_order: int = 0
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, what="название критерия", limit=_NAME_MAX))
        max_score = parse_score(self.max_score, what="Максимальный балл")
        if max_score <= 0:
            raise InvalidJudgingDataError("Максимальный балл критерия должен быть больше нуля.")
        object.__setattr__(self, "max_score", max_score)
        weight = parse_score(self.weight, what="Вес критерия")
        if weight <= 0:
            raise InvalidJudgingDataError("Вес критерия должен быть больше нуля.")
        object.__setattr__(self, "weight", weight)
        if self.sort_order < 0:
            raise InvalidJudgingDataError("Порядок критерия не может быть отрицательным.")
        description = str(self.description or "").strip() or None
        if description is not None and len(description) > 500:
            raise InvalidJudgingDataError("Пояснение к критерию — не длиннее 500 символов.")
        object.__setattr__(self, "description", description)

    def contribution(self, score: Score) -> Score:
        """What ``score`` on this criterion contributes to an act's total."""
        return (score * self.weight).quantize(_SCORE_EXPONENT)


@dataclass(frozen=True, slots=True)
class CriteriaSet:
    """The criteria one genre — or one nomination inside it — is judged on.

    :attr:`target_id` is the genre's or the nomination's id, depending on
    :attr:`scope`. The set is a value object rather than an entity: it is replaced
    wholesale when an organizer edits it, and only the criteria inside it have
    identities worth keeping.
    """

    scope: CriteriaScope
    target_id: uuid.UUID
    criteria: tuple[Criterion, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scope, CriteriaScope):
            raise InvalidJudgingDataError("Неизвестная область действия набора критериев.")
        ordered = tuple(sorted(self.criteria, key=lambda item: (item.sort_order, item.name)))
        seen: set[uuid.UUID] = set()
        for criterion in ordered:
            if criterion.id in seen:
                raise InvalidJudgingDataError("Один и тот же критерий указан дважды.")
            seen.add(criterion.id)
        object.__setattr__(self, "criteria", ordered)

    @property
    def is_empty(self) -> bool:
        return not self.criteria

    @property
    def max_total(self) -> Score:
        """The highest total one judge can give under this set."""
        total = sum((criterion.contribution(criterion.max_score) for criterion in self.criteria), Decimal(0))
        return Decimal(total).quantize(_SCORE_EXPONENT)


# ---------------------------------------------------------------------------
# Scoring rules
# ---------------------------------------------------------------------------


class AggregationMethod(StrEnum):
    """How several judges' totals become one number for the act.

    ``AVERAGE`` keeps the result on the same scale as one judge's sheet, so a band
    written for a ten-point sheet still means what it says when a judge falls ill and
    four score instead of five. ``SUM`` is what festivals that publish "набрано 47
    баллов из 50" mean, and it moves with the size of the panel — which is why the
    scale's bands and this choice have to be decided together.
    """

    AVERAGE = "AVERAGE"
    SUM = "SUM"


@dataclass(frozen=True, slots=True)
class ScoringRules:
    """How an act's own number is arrived at from the panel's sheets.

    :attr:`drop_highest` and :attr:`drop_lowest` are the classic guard against one
    judge deciding a result on their own. They are applied before aggregation, and only
    while enough sheets would survive: dropping both ends of a three-judge panel leaves
    one mark, which is the opposite of what the rule is for, so the domain refuses to
    drop anything that would leave fewer than three.
    """

    aggregation: AggregationMethod = AggregationMethod.AVERAGE
    drop_highest: bool = False
    drop_lowest: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.aggregation, AggregationMethod):
            raise InvalidJudgingDataError("Выберите, как считается итоговый балл.")

    @property
    def minimum_panel(self) -> int:
        """How many sheets an act needs before anything may be dropped."""
        dropped = int(self.drop_highest) + int(self.drop_lowest)
        return dropped + 3 if dropped else 0

    def aggregate(self, totals: Sequence[Score]) -> Score | None:
        """Turn one act's judge totals into its own score, or ``None`` if unjudged."""
        marks = sorted(totals)
        if not marks:
            return None
        if self.minimum_panel and len(marks) >= self.minimum_panel:
            if self.drop_lowest:
                marks = marks[1:]
            if self.drop_highest:
                marks = marks[:-1]
        total = sum(marks, Decimal(0))
        if self.aggregation is AggregationMethod.SUM:
            return Decimal(total).quantize(_SCORE_EXPONENT)
        return (Decimal(total) / Decimal(len(marks))).quantize(_SCORE_EXPONENT)


# ---------------------------------------------------------------------------
# Award scale
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AwardTier:
    """One step of the festival's award scale.

    :attr:`code` is what a protocol row stores and never changes; :attr:`label` is what
    everybody reads and may be corrected at any time. Keeping them apart is what lets
    an organizer fix "Лауреат 1 степени" to "Лауреат I степени" without rewriting
    results that have already been published.

    The band is inclusive at both ends and either end may be open: the top tier
    usually has no ceiling, and a participation diploma no floor. A tier with no band
    at all (both ``None``) is a name with no threshold — meaningful for a festival that
    runs on protocols, where nothing is scored and the scale is only a vocabulary.
    """

    code: str
    label: str
    min_score: Score | None = None
    max_score: Score | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        code = str(self.code or "").strip().upper()
        if not _TIER_CODE_RE.match(code):
            raise InvalidJudgingDataError("Код награды — латинские буквы, цифры и подчёркивание, начиная с буквы.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "label", _text(self.label, what="название награды", limit=_LABEL_MAX))
        minimum = parse_score(self.min_score, what="Нижний порог") if self.min_score is not None else None
        maximum = parse_score(self.max_score, what="Верхний порог") if self.max_score is not None else None
        if minimum is not None and maximum is not None and minimum > maximum:
            raise InvalidJudgingDataError(f"«{self.label}»: нижний порог больше верхнего.")
        object.__setattr__(self, "min_score", minimum)
        object.__setattr__(self, "max_score", maximum)
        if self.sort_order < 0:
            raise InvalidJudgingDataError("Порядок награды не может быть отрицательным.")

    @property
    def has_band(self) -> bool:
        return self.min_score is not None or self.max_score is not None

    def covers(self, score: Score) -> bool:
        """Whether ``score`` falls in this tier's band. A tier with no band covers nothing."""
        if not self.has_band:
            return False
        if self.min_score is not None and score < self.min_score:
            return False
        return not (self.max_score is not None and score > self.max_score)


#: The scale a festival starts with: the vocabulary this platform has always used,
#: with no thresholds attached. It is a *default*, not a fixed list — an organizer who
#: hands out "1 место" deletes all nine and writes their own. The codes match the ones
#: protocols have been storing since before the scale was configurable, so a festival
#: that never touches this screen keeps rendering exactly what it rendered before.
DEFAULT_AWARD_TIERS: Final[tuple[tuple[str, str], ...]] = (
    ("GRAND_PRIX", "Гран-при"),
    ("GRAND_PRIX_NOMINEE", "Номинант на Гран-при"),
    ("LAUREATE_I", "Лауреат I степени"),
    ("LAUREATE_II", "Лауреат II степени"),
    ("LAUREATE_III", "Лауреат III степени"),
    ("DIPLOMANT_I", "Дипломант I степени"),
    ("DIPLOMANT_II", "Дипломант II степени"),
    ("DIPLOMANT_III", "Дипломант III степени"),
    ("PARTICIPANT", "Диплом участника"),
)


@dataclass(frozen=True, slots=True)
class AwardScale:
    """The festival's whole award vocabulary, most senior first.

    One scale per festival, deliberately. A festival that called the same result "1
    место" in one genre and "Лауреат I степени" in another would be unreadable on the
    ceremony's running order and on a participant's diploma, and no organizer asking
    for flexible places is asking for that.

    Bands are checked for overlap on construction: two tiers claiming 90 points is not
    a preference, it is a scale that cannot answer the only question it is asked.
    """

    tiers: tuple[AwardTier, ...] = ()

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.tiers, key=lambda tier: (tier.sort_order, tier.label)))
        seen: set[str] = set()
        for tier in ordered:
            if tier.code in seen:
                raise InvalidJudgingDataError(f"Код награды «{tier.code}» указан дважды.")
            seen.add(tier.code)
        banded = [tier for tier in ordered if tier.has_band]
        for index, tier in enumerate(banded):
            for other in banded[index + 1 :]:
                if _bands_overlap(tier, other):
                    raise InvalidJudgingDataError(f"Диапазоны «{tier.label}» и «{other.label}» пересекаются.")
        object.__setattr__(self, "tiers", ordered)

    @classmethod
    def default(cls) -> AwardScale:
        """The platform's historical vocabulary, unbanded."""
        return cls(tiers=tuple(AwardTier(code=code, label=label, sort_order=index) for index, (code, label) in enumerate(DEFAULT_AWARD_TIERS)))

    @property
    def is_banded(self) -> bool:
        """Whether any tier can be reached by a score — what online judging needs."""
        return any(tier.has_band for tier in self.tiers)

    def by_code(self, code: str) -> AwardTier | None:
        """The tier ``code`` names, or ``None`` if the scale no longer has one."""
        wanted = str(code or "").strip().upper()
        return next((tier for tier in self.tiers if tier.code == wanted), None)

    def label_for(self, code: str) -> str | None:
        tier = self.by_code(code)
        return tier.label if tier is not None else None

    def tier_for_score(self, score: Score) -> AwardTier | None:
        """The award ``score`` earns, or ``None`` if it falls outside every band.

        Falling outside is a legal answer, not an error: a festival that awards nothing
        below 60 points has acts that finish with no award, and inventing one for them
        would be the platform overruling the organizer.
        """
        return next((tier for tier in self.tiers if tier.covers(score)), None)


def _bands_overlap(left: AwardTier, right: AwardTier) -> bool:
    low = left.min_score if left.min_score is not None else Decimal(0)
    high = left.max_score if left.max_score is not None else _SCORE_MAX
    other_low = right.min_score if right.min_score is not None else Decimal(0)
    other_high = right.max_score if right.max_score is not None else _SCORE_MAX
    return low <= other_high and other_low <= high


# ---------------------------------------------------------------------------
# What a result is reckoned within
# ---------------------------------------------------------------------------


class TallyDimension(StrEnum):
    """One axis a result may be reckoned within.

    Awards here are decided by the score alone, so these do not change who wins what —
    they decide how the results are *grouped*: which acts appear together on a sheet,
    on the hall's board, and in one protocol. An eight-year-old and a sixteen-year-old
    both clearing 90 points both take the top tier; what an organizer means by adding
    ``AGE_CATEGORY`` is that they should be announced apart.
    """

    CATEGORY = "CATEGORY"
    DISCIPLINE = "DISCIPLINE"
    AGE_CATEGORY = "AGE_CATEGORY"
    PARTICIPATION_FORMAT = "PARTICIPATION_FORMAT"


@dataclass(frozen=True, slots=True)
class TallyScope:
    """The axes this festival separates its results by.

    Always contains :attr:`TallyDimension.CATEGORY`: a protocol is a genre's document,
    which is the one grouping the rest of the platform already assumes, and a scope
    without it would put вокал and хореография on one sheet.
    """

    dimensions: frozenset[TallyDimension] = frozenset({TallyDimension.CATEGORY})

    def __post_init__(self) -> None:
        dimensions = frozenset(self.dimensions) | {TallyDimension.CATEGORY}
        for dimension in dimensions:
            if not isinstance(dimension, TallyDimension):
                raise InvalidJudgingDataError("Неизвестное измерение зачёта.")
        object.__setattr__(self, "dimensions", dimensions)

    @classmethod
    def default(cls) -> TallyScope:
        return cls()

    def __contains__(self, dimension: object) -> bool:
        return dimension in self.dimensions

    def ordered(self) -> tuple[TallyDimension, ...]:
        """The dimensions in a stable, human order (genre first, then finer cuts)."""
        order = (
            TallyDimension.CATEGORY,
            TallyDimension.DISCIPLINE,
            TallyDimension.AGE_CATEGORY,
            TallyDimension.PARTICIPATION_FORMAT,
        )
        return tuple(dimension for dimension in order if dimension in self.dimensions)


# ---------------------------------------------------------------------------
# The hall's board
# ---------------------------------------------------------------------------


class BoardVisibility(StrEnum):
    """How much of the panel's working the board shows.

    ``PER_JUDGE`` names every judge and their mark, the way figure skating does. It is
    the most convincing thing a hall can be shown and the most exposing thing a judge
    can be put through, which is exactly why it is the organizer's call and not ours.

    ``TOTAL_ONLY`` shows how many sheets are in and the act's own number once they are.
    """

    PER_JUDGE = "PER_JUDGE"
    TOTAL_ONLY = "TOTAL_ONLY"


class BoardReveal(StrEnum):
    """When a mark reaches the screen.

    ``IMMEDIATE`` puts it up as the judge presses send. ``AFTER_CLOSE`` holds everything
    until the host closes the act — which is also the moment marks stop being editable,
    so nothing a hall has read can change afterwards.
    """

    IMMEDIATE = "IMMEDIATE"
    AFTER_CLOSE = "AFTER_CLOSE"


@dataclass(frozen=True, slots=True)
class BoardSettings:
    """What the screen beside the stage shows, and when."""

    enabled: bool = False
    visibility: BoardVisibility = BoardVisibility.TOTAL_ONLY
    reveal: BoardReveal = BoardReveal.AFTER_CLOSE
    show_award: bool = True
    show_running_order: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.visibility, BoardVisibility):
            raise InvalidJudgingDataError("Выберите, что показывает табло.")
        if not isinstance(self.reveal, BoardReveal):
            raise InvalidJudgingDataError("Выберите, когда табло показывает оценки.")


# ---------------------------------------------------------------------------
# Lifecycle enums
# ---------------------------------------------------------------------------


class JuryMemberStatus(StrEnum):
    """Where a jury member is between being invited and being able to score.

    ``INVITED`` is a person the organizer has entered and written to; they hold a link
    and no account yet. ``ACTIVE`` is an accepted invitation with an account behind it —
    the only state that may score. ``REVOKED`` is a membership withdrawn; the marks
    already given stay, because they are what the jury decided.
    """

    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class PerformanceScoringStatus(StrEnum):
    """Whether an act is open to the panel.

    ``PENDING`` is an act the host has not reached. ``OPEN`` is the act on stage or just
    finished: sheets may be written and rewritten. ``CLOSED`` is the host's "готово" —
    marks freeze, and under ``AFTER_CLOSE`` this is when the hall sees them.

    Re-opening is allowed and deliberately so: a judge whose tablet dropped the
    connection is a normal event, and a platform that made closing final would be
    worked around by entering the mark as somebody else.
    """

    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


def parse_dimensions(values: Iterable[object]) -> TallyScope:
    """Read a tally scope off the wire, ignoring nothing silently."""
    dimensions: set[TallyDimension] = set()
    for value in values:
        try:
            dimensions.add(TallyDimension(str(value)))
        except ValueError as exc:
            raise InvalidJudgingDataError(f"Неизвестное измерение зачёта: {value!r}.") from exc
    return TallyScope(dimensions=frozenset(dimensions))
