"""Request/response serializers for the Judging API v1.

Field names are the API's camelCase wire keys (API-000 §7). Request serializers
validate **shape only** — whether a band overlaps another, whether a mark exceeds its
criterion's ceiling, whether a judge may write right now: all of that is the domain's,
and a serializer that decided any of it would be a second place those rules live.

Scores cross the wire as **strings**, not JSON numbers. A jury's arithmetic has to
round-trip exactly, and ``9.1`` through a double comes back as something that no longer
compares equal to the band it was typed for.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "AssignJuryRequestSerializer",
    "AwardScaleRequestSerializer",
    "BoardEnvelopeSerializer",
    "BoardRequestSerializer",
    "CriteriaRequestSerializer",
    "InviteJuryRequestSerializer",
    "JudgingProblemDetailSerializer",
    "JudgingSetupEnvelopeSerializer",
    "JuryListEnvelopeSerializer",
    "JuryMemberEnvelopeSerializer",
    "JurySeatListEnvelopeSerializer",
    "JuryTaskListEnvelopeSerializer",
    "RunningOrderEnvelopeSerializer",
    "ScoringRulesRequestSerializer",
    "ScoringStateEnvelopeSerializer",
    "ScoringStateListEnvelopeSerializer",
    "SubmitScorecardRequestSerializer",
    "TallyApplicationEnvelopeSerializer",
    "TallyApplyRequestSerializer",
    "TallyEnvelopeSerializer",
    "TallyScopeRequestSerializer",
    "UpdateJuryRequestSerializer",
]

#: How a score is bounded on the wire: eight digits, two of them after the point —
#: enough for a twenty-criterion sheet summed across a dozen judges.
_MAX_DIGITS = 8
_DECIMAL_PLACES = 2


def _score_field(**kwargs: object) -> serializers.DecimalField:
    """A score on the wire: a decimal, never a float. See the module docstring."""
    return serializers.DecimalField(max_digits=_MAX_DIGITS, decimal_places=_DECIMAL_PLACES, **kwargs)  # type: ignore[arg-type]


_AGGREGATION_CHOICES = ["AVERAGE", "SUM"]
_SCOPE_CHOICES = ["CATEGORY", "DISCIPLINE"]
_DIMENSION_CHOICES = ["CATEGORY", "DISCIPLINE", "AGE_CATEGORY", "PARTICIPATION_FORMAT"]
_VISIBILITY_CHOICES = ["PER_JUDGE", "TOTAL_ONLY"]
_REVEAL_CHOICES = ["IMMEDIATE", "AFTER_CLOSE"]


class _MetaSerializer(serializers.Serializer[dict[str, object]]):
    requestId = serializers.CharField()


#: RFC 9457 problem document (API-000 §8).
#:
#: Declared inline rather than as a class because ``type`` is a field name here and an
#: attribute of every DRF serializer — the same reason the Results edge next door does it
#: this way.
JudgingProblemDetailSerializer = inline_serializer(
    name="JudgingProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
    },
)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class _CriterionInputSerializer(serializers.Serializer[dict[str, object]]):
    """One line of a criteria sheet.

    ``id`` is optional and *load-bearing when present*: sending a criterion back with
    the id it came with is what keeps marks already given against it attached to it.
    """

    id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=200)
    maxScore = _score_field()
    weight = _score_field()
    sortOrder = serializers.IntegerField(required=False, default=0, min_value=0)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)


class CriteriaRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    scope = serializers.ChoiceField(choices=_SCOPE_CHOICES)
    targetId = serializers.UUIDField()
    criteria = _CriterionInputSerializer(many=True)


class _AwardTierInputSerializer(serializers.Serializer[dict[str, object]]):
    """One step of the scale. A blank band is legal — see ``AwardTier``."""

    code = serializers.CharField(max_length=64, required=False, allow_blank=True)
    label = serializers.CharField(max_length=120)  # type: ignore[assignment]
    minScore = _score_field(required=False, allow_null=True)
    maxScore = _score_field(required=False, allow_null=True)
    sortOrder = serializers.IntegerField(required=False, default=0, min_value=0)


class AwardScaleRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    tiers = _AwardTierInputSerializer(many=True)


class ScoringRulesRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    aggregation = serializers.ChoiceField(choices=_AGGREGATION_CHOICES)
    dropHighest = serializers.BooleanField(required=False, default=False)
    dropLowest = serializers.BooleanField(required=False, default=False)


class TallyScopeRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    dimensions = serializers.ListField(child=serializers.ChoiceField(choices=_DIMENSION_CHOICES))


class BoardRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    enabled = serializers.BooleanField()
    visibility = serializers.ChoiceField(choices=_VISIBILITY_CHOICES)
    reveal = serializers.ChoiceField(choices=_REVEAL_CHOICES)
    showAward = serializers.BooleanField(required=False, default=True)
    showRunningOrder = serializers.BooleanField(required=False, default=True)


class InviteJuryRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    fullName = serializers.CharField(max_length=200)
    email = serializers.EmailField(max_length=320)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    isChair = serializers.BooleanField(required=False, default=False)
    #: Empty means the whole festival, which is what a small panel wants.
    categoryIds = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)


class UpdateJuryRequestSerializer(serializers.Serializer[dict[str, object]]):
    fullName = serializers.CharField(max_length=200)
    email = serializers.EmailField(max_length=320)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    isChair = serializers.BooleanField(required=False, default=False)


class AssignJuryRequestSerializer(serializers.Serializer[dict[str, object]]):
    categoryIds = serializers.ListField(child=serializers.UUIDField())


class ScoringStateRequestSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.UUIDField()
    submissionId = serializers.UUIDField()
    closePrevious = serializers.BooleanField(required=False, default=True)


class TallyApplyRequestSerializer(serializers.Serializer[dict[str, object]]):
    """``createMissing`` opens a protocol for a genre that has none, from the programme."""

    createMissing = serializers.BooleanField(required=False, default=False)


class SubmitScorecardRequestSerializer(serializers.Serializer[dict[str, object]]):
    """One judge's sheet: a mark per criterion id, plus a note to the organizer."""

    competitionId = serializers.UUIDField()
    submissionId = serializers.UUIDField()
    scores = serializers.DictField(child=_score_field())
    comment = serializers.CharField(max_length=2000, required=False, allow_blank=True, allow_null=True)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class _CriterionSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    name = serializers.CharField()
    maxScore = serializers.CharField()
    weight = serializers.CharField()
    sortOrder = serializers.IntegerField()
    description = serializers.CharField(allow_null=True)


class _CriteriaSetSerializer(serializers.Serializer[dict[str, object]]):
    scope = serializers.CharField()
    targetId = serializers.CharField()
    targetName = serializers.CharField(allow_null=True)
    criteria = _CriterionSerializer(many=True)
    maxTotal = serializers.CharField()


class _AwardTierSerializer(serializers.Serializer[dict[str, object]]):
    code = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    minScore = serializers.CharField(allow_null=True)
    maxScore = serializers.CharField(allow_null=True)
    sortOrder = serializers.IntegerField()


class _NominationSerializer(serializers.Serializer[dict[str, object]]):
    categoryId = serializers.CharField()
    name = serializers.CharField()
    disciplines = serializers.ListField(child=serializers.DictField(child=serializers.CharField()))


class _JudgingSetupSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.CharField()
    onlineJudging = serializers.BooleanField()
    awardScale = _AwardTierSerializer(many=True)
    criteriaSets = _CriteriaSetSerializer(many=True)
    nominations = _NominationSerializer(many=True)
    aggregation = serializers.CharField()
    dropHighest = serializers.BooleanField()
    dropLowest = serializers.BooleanField()
    tallyDimensions = serializers.ListField(child=serializers.CharField())
    boardEnabled = serializers.BooleanField()
    boardVisibility = serializers.CharField()
    boardReveal = serializers.CharField()
    boardShowAward = serializers.BooleanField()
    boardShowRunningOrder = serializers.BooleanField()
    boardSlug = serializers.CharField(allow_null=True)
    boardPath = serializers.CharField(allow_null=True)
    juryCount = serializers.IntegerField()
    scaleIsBanded = serializers.BooleanField()
    updatedAt = serializers.DateTimeField(allow_null=True)


class _JuryMemberSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.CharField()
    fullName = serializers.CharField()
    email = serializers.CharField()
    title = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    isChair = serializers.BooleanField()
    categoryIds = serializers.ListField(child=serializers.CharField())
    categoryNames = serializers.ListField(child=serializers.CharField())
    sortOrder = serializers.IntegerField()
    hasAccount = serializers.BooleanField()
    invitedAt = serializers.DateTimeField(allow_null=True)
    acceptedAt = serializers.DateTimeField(allow_null=True)
    invitationPath = serializers.CharField(allow_null=True)


class _JurySeatSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.CharField()
    title = serializers.CharField()
    onlineJudging = serializers.BooleanField()
    isChair = serializers.BooleanField()
    categoryNames = serializers.ListField(child=serializers.CharField())
    startsOn = serializers.DateField(allow_null=True)
    endsOn = serializers.DateField(allow_null=True)
    venue = serializers.CharField(allow_null=True)
    pendingCount = serializers.IntegerField()
    hasOpenAct = serializers.BooleanField()


class _RunningOrderEntrySerializer(serializers.Serializer[dict[str, object]]):
    submissionId = serializers.CharField()
    number = serializers.IntegerField()
    title = serializers.CharField()
    categoryName = serializers.CharField(allow_null=True)
    disciplineName = serializers.CharField(allow_null=True)
    ageCategoryName = serializers.CharField(allow_null=True)
    organization = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    submittedCount = serializers.IntegerField()
    expectedJudges = serializers.IntegerField()
    score = serializers.CharField(allow_null=True)
    awardLabel = serializers.CharField(allow_null=True)


class _TallyApplicationSerializer(serializers.Serializer[dict[str, object]]):
    rowsChanged = serializers.IntegerField()
    protocolsCreated = serializers.IntegerField()
    missingProtocols = serializers.ListField(child=serializers.CharField())


class _JudgeScoreSerializer(serializers.Serializer[dict[str, object]]):
    criterionId = serializers.CharField()
    score = serializers.CharField()


class _JuryTaskSerializer(serializers.Serializer[dict[str, object]]):
    submissionId = serializers.CharField()
    number = serializers.IntegerField()
    title = serializers.CharField()
    categoryId = serializers.CharField()
    categoryName = serializers.CharField(allow_null=True)
    disciplineName = serializers.CharField(allow_null=True)
    ageCategoryName = serializers.CharField(allow_null=True)
    participationFormatName = serializers.CharField(allow_null=True)
    organization = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    criteria = _CriterionSerializer(many=True)
    myScores = _JudgeScoreSerializer(many=True)
    myComment = serializers.CharField(allow_null=True)
    myTotal = serializers.CharField(allow_null=True)
    submittedAt = serializers.DateTimeField(allow_null=True)
    canScore = serializers.BooleanField()
    maxTotal = serializers.CharField()


class _ScorecardSerializer(serializers.Serializer[dict[str, object]]):
    juryMemberId = serializers.CharField()
    juryMemberName = serializers.CharField()
    scores = _JudgeScoreSerializer(many=True)
    total = serializers.CharField()
    comment = serializers.CharField(allow_null=True)
    submittedAt = serializers.DateTimeField(allow_null=True)
    submitted = serializers.BooleanField()


class _PerformanceTallySerializer(serializers.Serializer[dict[str, object]]):
    submissionId = serializers.CharField()
    number = serializers.IntegerField()
    title = serializers.CharField()
    organization = serializers.CharField(allow_null=True)
    score = serializers.CharField(allow_null=True)
    maxScore = serializers.CharField()
    awardCode = serializers.CharField(allow_null=True)
    awardLabel = serializers.CharField(allow_null=True)
    submittedCount = serializers.IntegerField()
    expectedJudges = serializers.IntegerField()
    status = serializers.CharField()
    scorecards = _ScorecardSerializer(many=True)


class _TallyGroupSerializer(serializers.Serializer[dict[str, object]]):
    key = serializers.CharField()
    heading = serializers.CharField()
    categoryId = serializers.CharField(allow_null=True)
    tallies = _PerformanceTallySerializer(many=True)


class _TallySheetSerializer(serializers.Serializer[dict[str, object]]):
    competitionId = serializers.CharField()
    groups = _TallyGroupSerializer(many=True)
    aggregation = serializers.CharField()
    scaleIsBanded = serializers.BooleanField()
    unawardedCount = serializers.IntegerField()


class _ScoringStateSerializer(serializers.Serializer[dict[str, object]]):
    submissionId = serializers.CharField()
    status = serializers.CharField()
    openedAt = serializers.DateTimeField(allow_null=True)
    closedAt = serializers.DateTimeField(allow_null=True)


class _BoardJudgeSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField()
    total = serializers.CharField(allow_null=True)


class _BoardEntrySerializer(serializers.Serializer[dict[str, object]]):
    number = serializers.IntegerField()
    title = serializers.CharField()
    organization = serializers.CharField(allow_null=True)
    categoryName = serializers.CharField(allow_null=True)
    ageCategoryName = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    score = serializers.CharField(allow_null=True)
    maxScore = serializers.CharField()
    awardLabel = serializers.CharField(allow_null=True)
    submittedCount = serializers.IntegerField()
    expectedJudges = serializers.IntegerField()
    judges = _BoardJudgeSerializer(many=True)


class _BoardSerializer(serializers.Serializer[dict[str, object]]):
    competitionTitle = serializers.CharField()
    visibility = serializers.CharField()
    reveal = serializers.CharField()
    showAward = serializers.BooleanField()
    current = _BoardEntrySerializer(allow_null=True)
    recent = _BoardEntrySerializer(many=True)


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


class JudgingSetupEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _JudgingSetupSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class JuryListEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _JuryMemberSerializer(many=True)  # type: ignore[assignment]
    meta = _MetaSerializer()


class JuryMemberEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _JuryMemberSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class JuryTaskListEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _JuryTaskSerializer(many=True)  # type: ignore[assignment]
    meta = _MetaSerializer()


class JuryTaskEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _JuryTaskSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class JurySeatListEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    """The festivals this account judges — the judge's own way back in."""

    data = _JurySeatSerializer(many=True)  # type: ignore[assignment]
    meta = _MetaSerializer()


class RunningOrderEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    """The programme in programme order — the host's screen."""

    data = _RunningOrderEntrySerializer(many=True)  # type: ignore[assignment]
    meta = _MetaSerializer()


class TallyApplicationEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _TallyApplicationSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class TallyEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _TallySheetSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class ScoringStateEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _ScoringStateSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()


class ScoringStateListEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    """Every act's state at once — the host's screen reads the whole programme."""

    data = _ScoringStateSerializer(many=True)  # type: ignore[assignment]
    meta = _MetaSerializer()


class BoardEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    data = _BoardSerializer()  # type: ignore[assignment]
    meta = _MetaSerializer()
