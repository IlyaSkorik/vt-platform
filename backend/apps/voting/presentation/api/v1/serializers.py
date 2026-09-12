"""Request/response serializers for the Voting REST API v1.

Request serializers validate shape only — ranges, lengths and types the domain
would otherwise have to re-derive from a raw payload. Every *rule* (a window that
closes before it opens, a ballot too small to open) stays in the domain, so it
holds no matter which edge asks.

Response serializers exist so drf-spectacular renders an accurate OpenAPI 3.1
contract (API-000 §25); the views build their bodies from DTOs.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.voting.domain.value_objects import (
    BALLOT_TITLE_MAX,
    COOLDOWN_MAX_HOURS,
    NOMINEE_FIELD_MAX,
    VOTES_PER_VOTER_MAX,
    BallotStatus,
    RevealPolicy,
)

__all__ = [
    "AddNomineeRequestSerializer",
    "BallotDetailSerializer",
    "BallotProblemDetailSerializer",
    "BallotSummarySerializer",
    "CastVoteRequestSerializer",
    "CreateBallotRequestSerializer",
    "EditNomineeRequestSerializer",
    "ImportPreviewSerializer",
    "NomineeSerializer",
    "PublicBallotSerializer",
    "PublicNomineeSerializer",
    "ReorderNomineesRequestSerializer",
    "SeedFromProgramRequestSerializer",
    "UpdateBallotRequestSerializer",
    "VoteReceiptSerializer",
]

_STATUSES = [status.value for status in BallotStatus]
_REVEALS = [policy.value for policy in RevealPolicy]


class _BallotRulesMixin(serializers.Serializer[dict[str, object]]):
    """The three settings that decide how a ballot behaves."""

    votesPerVoter = serializers.IntegerField(min_value=1, max_value=VOTES_PER_VOTER_MAX, required=False)
    cooldownHours = serializers.IntegerField(min_value=0, max_value=COOLDOWN_MAX_HOURS, required=False)
    reveal = serializers.ChoiceField(choices=_REVEALS, required=False)


class CreateBallotRequestSerializer(_BallotRulesMixin):
    """Start a ballot.

    ``competitionId`` is optional, and that is the feature rather than a loose end:
    a festival that has not moved onto the platform gets the same ballot as one
    that has.
    """

    title = serializers.CharField(max_length=BALLOT_TITLE_MAX)
    competitionId = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    opensAt = serializers.DateTimeField(required=False, allow_null=True)
    closesAt = serializers.DateTimeField(required=False, allow_null=True)


class UpdateBallotRequestSerializer(_BallotRulesMixin):
    """Change a ballot's wording or its rules. Absent fields are left alone."""

    title = serializers.CharField(max_length=BALLOT_TITLE_MAX, required=False)
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    opensAt = serializers.DateTimeField(required=False, allow_null=True)
    closesAt = serializers.DateTimeField(required=False, allow_null=True)


class _NomineeFieldsMixin(serializers.Serializer[dict[str, object]]):
    subtitle = serializers.CharField(max_length=NOMINEE_FIELD_MAX, required=False, allow_blank=True)
    city = serializers.CharField(max_length=NOMINEE_FIELD_MAX, required=False, allow_blank=True)
    photo = serializers.CharField(max_length=1024, required=False, allow_blank=True, allow_null=True)
    number = serializers.IntegerField(min_value=0, max_value=100_000, required=False, allow_null=True)


class AddNomineeRequestSerializer(_NomineeFieldsMixin):
    """Put one more nominee on the ballot."""

    title = serializers.CharField(max_length=NOMINEE_FIELD_MAX)


class EditNomineeRequestSerializer(_NomineeFieldsMixin):
    """Correct a nominee's card. Absent fields are left alone."""

    title = serializers.CharField(max_length=NOMINEE_FIELD_MAX, required=False)


class ReorderNomineesRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Rearrange the list — every nominee named exactly once."""

    order = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class SeedFromProgramRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Fill the list from a running order of the festival this ballot belongs to."""

    programId = serializers.UUIDField()


class CastVoteRequestSerializer(serializers.Serializer[dict[str, object]]):
    """One person's votes.

    A list rather than a single id, so a ballot allowing several picks accepts or
    refuses the whole submission at once instead of leaving somebody with two of
    their three votes spent and an error on screen.
    """

    nomineeIds = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        max_length=VOTES_PER_VOTER_MAX,
    )


class NomineeSerializer(serializers.Serializer[dict[str, object]]):
    """One nominee as the organizer sees them."""

    id = serializers.UUIDField()
    position = serializers.IntegerField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    photo = serializers.CharField(allow_null=True)
    number = serializers.IntegerField(allow_null=True)
    withdrawn = serializers.BooleanField()
    votes = serializers.IntegerField()
    submissionId = serializers.UUIDField(allow_null=True, required=False)
    programItemId = serializers.UUIDField(allow_null=True, required=False)


class BallotSummarySerializer(serializers.Serializer[dict[str, object]]):
    """One row of the organizer's ballot list."""

    id = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.ChoiceField(choices=_STATUSES)
    competitionId = serializers.UUIDField(allow_null=True)
    standalone = serializers.BooleanField()
    nominees = serializers.IntegerField()
    totalVotes = serializers.IntegerField()
    opensAt = serializers.DateTimeField(allow_null=True)
    closesAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()


class BallotDetailSerializer(serializers.Serializer[dict[str, object]]):
    """The whole ballot as the organizer edits it."""

    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    slug = serializers.CharField()
    status = serializers.ChoiceField(choices=_STATUSES)
    competitionId = serializers.UUIDField(allow_null=True)
    standalone = serializers.BooleanField()
    opensAt = serializers.DateTimeField(allow_null=True)
    closesAt = serializers.DateTimeField(allow_null=True)
    votesPerVoter = serializers.IntegerField()
    cooldownHours = serializers.IntegerField()
    reveal = serializers.ChoiceField(choices=_REVEALS)
    nominees = NomineeSerializer(many=True)
    totalVotes = serializers.IntegerField()
    voters = serializers.IntegerField()
    createdAt = serializers.DateTimeField(allow_null=True)
    updatedAt = serializers.DateTimeField(allow_null=True)


class PublicNomineeSerializer(serializers.Serializer[dict[str, object]]):
    """One nominee as the audience sees them.

    ``votes`` is null — absent, not zero — whenever the reveal policy says the
    count is not for the public yet, so a page cannot render a nought for something
    it merely is not allowed to know.
    """

    id = serializers.UUIDField()
    position = serializers.IntegerField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    photo = serializers.CharField(allow_null=True)
    number = serializers.IntegerField(allow_null=True)
    votes = serializers.IntegerField(allow_null=True)
    chosen = serializers.BooleanField()


class PublicBallotSerializer(serializers.Serializer[dict[str, object]]):
    """The voting page."""

    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    slug = serializers.CharField()
    status = serializers.ChoiceField(choices=_STATUSES)
    open = serializers.BooleanField()
    votesPerVoter = serializers.IntegerField()
    votesLeft = serializers.IntegerField()
    revealTotals = serializers.BooleanField()
    nominees = PublicNomineeSerializer(many=True)
    totalVotes = serializers.IntegerField(allow_null=True)
    closesAt = serializers.DateTimeField(allow_null=True)
    closedReason = serializers.CharField(allow_null=True)


class VoteReceiptSerializer(serializers.Serializer[dict[str, object]]):
    """What comes back the moment somebody votes."""

    ballot = PublicBallotSerializer()
    accepted = serializers.ListField(child=serializers.UUIDField())


# Both of these are built with ``inline_serializer`` rather than declared as
# classes, because their field names — ``errors``, ``instance``, ``data`` — collide
# with attributes DRF's ``Serializer`` already defines. They exist only to shape the
# OpenAPI contract (API-000 §7, §8), never to validate anything.

ImportPreviewSerializer = inline_serializer(
    name="ImportPreview",
    fields={
        "added": NomineeSerializer(many=True),
        # ``{row, message}`` per rejected line, with the row number Excel shows —
        # the number the organizer will go looking for.
        "errors": serializers.ListField(child=serializers.DictField()),
        "missingColumns": serializers.ListField(child=serializers.CharField()),
        "dryRun": serializers.BooleanField(),
    },
)

BallotProblemDetailSerializer = inline_serializer(
    name="BallotProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
    },
)
