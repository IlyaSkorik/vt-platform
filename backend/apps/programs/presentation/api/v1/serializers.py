"""Request/response serializers for the organizer Programs API v1.

Field names are the API's camelCase wire keys (API-000 §7). Request serializers
validate shape only - every business rule belongs to the domain, so a serializer here
never decides whether an act may be scheduled or whether a reorder is complete.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.programs.domain.value_objects import (
    BUFFER_MAX_SECONDS,
    DURATION_MAX_SECONDS,
    ProgramColumn,
    ProgramItemKind,
)

__all__ = [
    "COLUMN_KEYS",
    "AddBlockRequestSerializer",
    "AddPerformanceRequestSerializer",
    "CreateProgramRequestSerializer",
    "CreateShareRequestSerializer",
    "EditItemRequestSerializer",
    "ProgramCandidateSerializer",
    "ProgramDetailSerializer",
    "ProgramProblemDetailSerializer",
    "ProgramShareResourceSerializer",
    "ProgramSummarySerializer",
    "ReorderItemsRequestSerializer",
    "UpdateProgramRequestSerializer",
    "UpdateShareRequestSerializer",
]

#: The kinds a client may create through the block endpoint - every kind except the
#: performance, which is created by referencing an act instead of a title.
BLOCK_KINDS = [kind.value for kind in ProgramItemKind if not kind.binds_performance]

#: The columns a programme table can carry, and therefore what a public edition may be
#: cut to. Enumerated from the domain so the contract cannot drift from it.
COLUMN_KEYS = [column.value for column in ProgramColumn]


class CreateProgramRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a create-program body."""

    competitionId = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    nominationId = serializers.UUIDField(required=False, allow_null=True)
    bufferSeconds = serializers.IntegerField(required=False, min_value=0, max_value=BUFFER_MAX_SECONDS)
    startsAt = serializers.DateTimeField(required=False, allow_null=True)


class UpdateProgramRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a partial program update.

    An absent field means "unchanged"; ``startsAt: null`` explicitly drops the start
    time, which is how a program goes back to being an untimed running order.
    """

    name = serializers.CharField(required=False, max_length=200)
    bufferSeconds = serializers.IntegerField(required=False, min_value=0, max_value=BUFFER_MAX_SECONDS)
    startsAt = serializers.DateTimeField(required=False, allow_null=True)


class AddPerformanceRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-performance body."""

    submissionId = serializers.UUIDField()
    position = serializers.IntegerField(required=False, min_value=1)
    durationSeconds = serializers.IntegerField(required=False, min_value=1, max_value=DURATION_MAX_SECONDS)


class AddBlockRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-block body (a break, and later an opening or an award)."""

    title = serializers.CharField(max_length=200)
    durationSeconds = serializers.IntegerField(min_value=1, max_value=DURATION_MAX_SECONDS)
    kind = serializers.ChoiceField(choices=BLOCK_KINDS, required=False, default=ProgramItemKind.BREAK.value)
    position = serializers.IntegerField(required=False, min_value=1)


class EditItemRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an edit-item body (retitle a block, resize any slot)."""

    title = serializers.CharField(required=False, max_length=200)
    durationSeconds = serializers.IntegerField(required=False, min_value=1, max_value=DURATION_MAX_SECONDS)


class ReorderItemsRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a reorder body: the complete new order, top to bottom."""

    itemIds = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class CreateShareRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a create-public-program body.

    ``columns`` is the selection that defines the edition - which columns of the table
    its reader sees. Omitting it publishes the default columns.

    Omitting ``itemIds`` (or sending an empty list) publishes every row and keeps
    following the programme - what a screen by the stage wants.
    """

    name = serializers.CharField(max_length=200)
    columns = serializers.ListField(child=serializers.ChoiceField(choices=COLUMN_KEYS), required=False, allow_empty=True)
    itemIds = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)


class UpdateShareRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a rename/re-column body for a published edition (its slug is permanent)."""

    name = serializers.CharField(required=False, max_length=200)
    columns = serializers.ListField(child=serializers.ChoiceField(choices=COLUMN_KEYS), required=False, allow_empty=True)


class _SchedulePositionSerializer(serializers.Serializer[dict[str, object]]):
    position = serializers.IntegerField()
    offsetSeconds = serializers.IntegerField()
    slotSeconds = serializers.IntegerField()
    startsAt = serializers.DateTimeField(allow_null=True)
    endsAt = serializers.DateTimeField(allow_null=True)


def _column_schema(*, many: bool = False) -> serializers.BaseSerializer[dict[str, object]]:
    """One column of the programme table: its stable key and its header.

    Declared inline because ``label`` is a serializer attribute in DRF, and the wire
    contract's field name wins.
    """
    return inline_serializer(
        name="ProgramColumn",
        fields={"key": serializers.ChoiceField(choices=COLUMN_KEYS), "label": serializers.CharField()},
        many=many,
    )


class ProgramItemResourceSerializer(serializers.Serializer[dict[str, object]]):
    """One row of the programme table, with its computed place on the timeline."""

    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=[kind.value for kind in ProgramItemKind])
    title = serializers.CharField()
    #: The participant's permanent number, unchanged by a reorder.
    number = serializers.IntegerField()
    durationSeconds = serializers.IntegerField()
    schedule = _SchedulePositionSerializer()
    submissionId = serializers.UUIDField(allow_null=True)
    leadParticipant = serializers.CharField(allow_null=True)
    participants = serializers.ListField(child=serializers.CharField())
    teachers = serializers.ListField(child=serializers.CharField())
    nomination = serializers.CharField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    ageCategory = serializers.CharField(allow_null=True)
    participantGroup = serializers.CharField(allow_null=True)
    participationFormat = serializers.CharField(allow_null=True)
    organization = serializers.CharField(allow_null=True)
    comment = serializers.CharField(allow_null=True)
    missingPerformance = serializers.BooleanField()


class ProgramShareResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A public edition of the program: the columns it shows and the path it lives at."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    path = serializers.CharField()
    columns = _column_schema(many=True)
    itemCount = serializers.IntegerField()
    coversWholeProgram = serializers.BooleanField()
    createdAt = serializers.DateTimeField(allow_null=True)


class ProgramDetailSerializer(serializers.Serializer[dict[str, object]]):
    """One program in full: settings, timetable and public links."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    nominationId = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    bufferSeconds = serializers.IntegerField()
    startsAt = serializers.DateTimeField(allow_null=True)
    items = ProgramItemResourceSerializer(many=True)
    shares = ProgramShareResourceSerializer(many=True)
    availableColumns = _column_schema(many=True)
    #: False while the programme is being assembled - numbers then follow the order.
    numbersFrozen = serializers.BooleanField()
    numbersFrozenAt = serializers.DateTimeField(allow_null=True)
    totalSeconds = serializers.IntegerField()
    endsAt = serializers.DateTimeField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()
    version = serializers.IntegerField()


class ProgramSummarySerializer(serializers.Serializer[dict[str, object]]):
    """A program as it appears in a list."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    nominationId = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    bufferSeconds = serializers.IntegerField()
    startsAt = serializers.DateTimeField(allow_null=True)
    itemCount = serializers.IntegerField()
    performanceCount = serializers.IntegerField()
    totalSeconds = serializers.IntegerField()
    shareCount = serializers.IntegerField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class ProgramCandidateSerializer(serializers.Serializer[dict[str, object]]):
    """A competing act that has no slot in this program yet."""

    submissionId = serializers.UUIDField()
    title = serializers.CharField()
    durationSeconds = serializers.IntegerField()
    nomination = serializers.CharField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    ageCategory = serializers.CharField(allow_null=True)
    participantGroup = serializers.CharField(allow_null=True)
    participationFormat = serializers.CharField(allow_null=True)
    participants = serializers.ListField(child=serializers.CharField())
    teachers = serializers.ListField(child=serializers.CharField())
    organization = serializers.CharField(allow_null=True)
    comment = serializers.CharField(allow_null=True)


# RFC 9457 Problem Details (API-000 §8). Declared inline because ``instance`` is a
# serializer attribute in DRF, and the wire contract's field name wins.
ProgramProblemDetailSerializer = inline_serializer(
    name="ProgramProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
        "errors": serializers.ListField(child=serializers.DictField(), required=False),
    },
)
