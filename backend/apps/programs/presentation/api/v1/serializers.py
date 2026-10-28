"""Request/response serializers for the organizer Programs API v1.

Field names are the API's camelCase wire keys (API-000 §7). Request serializers
validate shape only - every business rule belongs to the domain, so a serializer here
never decides whether an act may be scheduled or whether a reorder is complete.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.programs.domain.value_objects import (
    BREAK_AFTER_ITEMS_MAX,
    BUFFER_MAX_SECONDS,
    CELL_VALUE_MAX,
    DURATION_MAX_SECONDS,
    HOST_NOTE_MAX,
    REPEAT_GAP_MAX,
    BreakRule,
    GroupingAxis,
    PerformanceOrder,
    ProgramColumn,
    ProgramItemKind,
    ProgramItemProgress,
)

__all__ = [
    "COLUMN_KEYS",
    "AddBlockRequestSerializer",
    "AddPerformanceRequestSerializer",
    "ArrangeProgramRequestSerializer",
    "ArrangementResourceSerializer",
    "ColumnRequestSerializer",
    "CreateProgramRequestSerializer",
    "CreateShareRequestSerializer",
    "EditItemRequestSerializer",
    "FillCellsRequestSerializer",
    "ProgramCandidateSerializer",
    "ProgramDetailSerializer",
    "ProgramProblemDetailSerializer",
    "ProgramShareResourceSerializer",
    "ProgramSummarySerializer",
    "ReorderItemsRequestSerializer",
    "SetBackstageRequestSerializer",
    "SetHostNoteRequestSerializer",
    "SetProgressRequestSerializer",
    "UpdateProgramRequestSerializer",
    "UpdateShareRequestSerializer",
]

#: The kinds a client may create through the block endpoint - every kind except the
#: performance, which is created by referencing an act instead of a title.
BLOCK_KINDS = [kind.value for kind in ProgramItemKind if not kind.binds_performance]

#: The vocabulary of the generator, enumerated from the domain so a settings form can
#: never offer a rule the algorithm does not have.
GROUPING_AXES = [axis.value for axis in GroupingAxis]
PERFORMANCE_ORDERS = [order.value for order in PerformanceOrder]
BREAK_RULES = [rule.value for rule in BreakRule]

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


class ArrangeProgramRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate the rules a programme is to be generated from.

    Every field is optional, and an **entirely empty body means "the rules this
    programme was last built from"** - which is what makes "пересобрать" a button
    without a form. A body that is present is read as complete: a field left out takes
    the default, not the saved value, so the dialog on screen is what gets generated.

    Shape only, as ever. Which combinations hold together - a break rule with nothing to
    insert, an interval of zero - is the domain's judgement, and
    :class:`~apps.programs.domain.value_objects.ArrangementSettings` makes it.
    """

    #: The axes to group along, in the order they are applied. An empty list means
    #: "do not group": one sequence, ordered and spaced like any other.
    grouping = serializers.ListField(child=serializers.ChoiceField(choices=GROUPING_AXES), required=False, allow_empty=True)
    orderWithinGroup = serializers.ChoiceField(choices=PERFORMANCE_ORDERS, required=False)
    breakRule = serializers.ChoiceField(choices=BREAK_RULES, required=False)
    breakAfterSeconds = serializers.IntegerField(required=False, min_value=0, max_value=DURATION_MAX_SECONDS)
    breakAfterItems = serializers.IntegerField(required=False, min_value=0, max_value=BREAK_AFTER_ITEMS_MAX)
    breakTitle = serializers.CharField(required=False, max_length=200)
    breakDurationSeconds = serializers.IntegerField(required=False, min_value=1, max_value=DURATION_MAX_SECONDS)
    #: How many slots must separate two acts of the same participant; 0 turns it off.
    repeatGap = serializers.IntegerField(required=False, min_value=0, max_value=REPEAT_GAP_MAX)
    #: Naming or timing a service block is how it is switched on.
    openingTitle = serializers.CharField(required=False, max_length=200)
    openingDurationSeconds = serializers.IntegerField(required=False, min_value=1, max_value=DURATION_MAX_SECONDS)
    awardTitle = serializers.CharField(required=False, max_length=200)
    awardDurationSeconds = serializers.IntegerField(required=False, min_value=1, max_value=DURATION_MAX_SECONDS)


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
    # A key is either a built-in column name or ``custom:<uuid>``; the domain validates
    # which, because only it knows this programme's own columns.
    columns = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    itemIds = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    controlsRunningOrder = serializers.BooleanField(required=False, default=False)


class AnnounceProgramRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an announcement body. Everything about *who* is decided by the edition."""

    #: A line of the organizer's own above the running order, optional and short: this
    #: is a covering note, not a second letter.
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AnnouncementResourceSerializer(serializers.Serializer[dict[str, object]]):
    """What came of an announcement: who was written to, and who could not be."""

    notified = serializers.IntegerField()
    acts = serializers.IntegerField()
    skipped = serializers.IntegerField()


class UpdateShareRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a rename/re-column body for a published edition (its slug is permanent)."""

    name = serializers.CharField(required=False, max_length=200)
    columns = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    controlsRunningOrder = serializers.BooleanField(required=False)


class ColumnRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate the title of a custom column ("Микрофон", "Реквизит")."""

    title = serializers.CharField(max_length=120)


class FillCellsRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate hand-filled values for one row, keyed by custom column key.

    A blank value clears the cell, so there is no separate verb for removing one.
    """

    values = serializers.DictField(child=serializers.CharField(allow_blank=True, max_length=CELL_VALUE_MAX))


class SetProgressRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a progress update from the host's link."""

    progress = serializers.ChoiceField(choices=[state.value for state in ProgramItemProgress])


class SetBackstageRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate the host's backstage mark.

    The whole answer, not a toggle: the host may have the same link open on two screens,
    and "invert whatever is there" sent from both lands wherever the second request
    happened to find it.
    """

    backstage = serializers.BooleanField()


class SetHostNoteRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate the host's own note on one row. Blank clears it."""

    note = serializers.CharField(allow_blank=True, max_length=HOST_NOTE_MAX, trim_whitespace=True)


class _SchedulePositionSerializer(serializers.Serializer[dict[str, object]]):
    position = serializers.IntegerField()
    offsetSeconds = serializers.IntegerField()
    slotSeconds = serializers.IntegerField()
    startsAt = serializers.DateTimeField(allow_null=True)
    endsAt = serializers.DateTimeField(allow_null=True)


def _column_schema(*, many: bool = False) -> serializers.BaseSerializer[dict[str, object]]:
    """One column of the programme table: its stable key, its header, and whether it is
    one the organizer added themselves.

    Declared inline because ``label`` is a serializer attribute in DRF, and the wire
    contract's field name wins.
    """
    return inline_serializer(
        name="ProgramColumn",
        fields={
            "key": serializers.CharField(),
            "label": serializers.CharField(),
            "custom": serializers.BooleanField(),
            "sensitive": serializers.BooleanField(),
        },
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
    participants = serializers.ListField(child=serializers.CharField())
    #: The headcount on stage, not the number of performer rows.
    participantCount = serializers.IntegerField()
    teachers = serializers.ListField(child=serializers.CharField())
    #: Phones to ring about this act: its teachers', or the applicant's if none.
    contacts = serializers.ListField(child=serializers.CharField())
    nomination = serializers.CharField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    ageCategory = serializers.CharField(allow_null=True)
    participantGroup = serializers.CharField(allow_null=True)
    participationFormat = serializers.CharField(allow_null=True)
    organization = serializers.CharField(allow_null=True)
    comment = serializers.CharField(allow_null=True)
    missingPerformance = serializers.BooleanField()
    #: Hand-filled values keyed by custom column key.
    customValues = serializers.DictField(child=serializers.CharField(allow_blank=True))
    progress = serializers.ChoiceField(choices=[state.value for state in ProgramItemProgress])


class ProgramShareResourceSerializer(serializers.Serializer[dict[str, object]]):
    """A public edition of the program: the columns it shows and the path it lives at."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    path = serializers.CharField()
    columns = _column_schema(many=True)
    itemCount = serializers.IntegerField()
    coversWholeProgram = serializers.BooleanField()
    controlsRunningOrder = serializers.BooleanField()
    createdAt = serializers.DateTimeField(allow_null=True)


class ArrangementResourceSerializer(serializers.Serializer[dict[str, object]]):
    """The generation rules a programme carries, as the settings dialog reads them back."""

    grouping = serializers.ListField(child=serializers.ChoiceField(choices=GROUPING_AXES))
    orderWithinGroup = serializers.ChoiceField(choices=PERFORMANCE_ORDERS)
    breakRule = serializers.ChoiceField(choices=BREAK_RULES)
    breakAfterSeconds = serializers.IntegerField()
    breakAfterItems = serializers.IntegerField()
    breakTitle = serializers.CharField(allow_null=True)
    breakDurationSeconds = serializers.IntegerField(allow_null=True)
    repeatGap = serializers.IntegerField()
    openingTitle = serializers.CharField(allow_null=True)
    openingDurationSeconds = serializers.IntegerField(allow_null=True)
    awardTitle = serializers.CharField(allow_null=True)
    awardDurationSeconds = serializers.IntegerField(allow_null=True)


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
    #: Null for a programme that was only ever built by hand.
    arrangement = ArrangementResourceSerializer(allow_null=True)
    #: True only between a rebuild and the undo that consumes it.
    canUndoArrange = serializers.BooleanField()
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
