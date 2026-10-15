"""Request/response serializers for the organizer Results API v1.

Field names are the API's camelCase wire keys (API-000 §7). Request serializers validate
shape only - every business rule belongs to the domain, so a serializer here never decides
whether an act may be awarded or whether a protocol may be published.

Awards are carried as **codes**, not as a fixed enumeration: a festival writes its own
award scale (see the Judging context), so the set of valid codes is per-competition and
cannot be pinned in a contract shared by all of them. The shape is still validated - a
code, not a free-text degree - and the domain's ``parse_award`` is what enforces it.
:data:`AWARD_VALUES` remains as documentation of the defaults every festival starts with.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.results.domain.value_objects import AwardKind, ProtocolColumn, ProtocolStatus

__all__ = [
    "AWARD_VALUES",
    "COLUMN_KEYS",
    "PROTOCOL_STATUS_VALUES",
    "AddRowRequestSerializer",
    "AwardRowsRequestSerializer",
    "CreateProtocolRequestSerializer",
    "ProtocolCandidateSerializer",
    "ProtocolDetailSerializer",
    "ProtocolProblemDetailSerializer",
    "ProtocolSummarySerializer",
    "PublicationResultSerializer",
    "PublishProtocolRequestSerializer",
    "ReorderRowsRequestSerializer",
    "UpdateProtocolRequestSerializer",
]

#: The award vocabulary a festival **starts** with, enumerated from the domain. Not a
#: constraint on the wire - see the module docstring - but what a client should expect to
#: see for a festival whose organizer never edited the scale.
AWARD_VALUES = [kind.value for kind in AwardKind]

#: How long an award code may be. Matches the domain's own bound.
_AWARD_CODE_MAX = 64

#: The columns a protocol table can carry, and therefore what a published page may be cut
#: to.
COLUMN_KEYS = [column.value for column in ProtocolColumn]

#: Whether a protocol's results are public. Named (and exported) rather than kept private
#: because ``ENUM_NAME_OVERRIDES`` pins the generated client's type to this very list.
PROTOCOL_STATUS_VALUES = [status.value for status in ProtocolStatus]


class CreateProtocolRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a create-protocol body.

    ``name`` is optional: a protocol with no name given takes its nomination's, which is
    what an organizer would have typed anyway. ``seed`` defaults on - the point of opening
    a protocol is to get the day's running order in it.
    """

    competitionId = serializers.UUIDField()
    nominationId = serializers.UUIDField()
    name = serializers.CharField(required=False, max_length=200)
    columns = serializers.ListField(child=serializers.ChoiceField(choices=COLUMN_KEYS), required=False, allow_empty=True)
    seed = serializers.BooleanField(required=False, default=True)


class UpdateProtocolRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a partial protocol update.

    An absent field means "unchanged"; an empty ``columns`` list resets the public page to
    the default column set rather than publishing nothing.
    """

    name = serializers.CharField(required=False, max_length=200)
    columns = serializers.ListField(child=serializers.ChoiceField(choices=COLUMN_KEYS), required=False, allow_empty=True)


class AddRowRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an add-row body - the act slotted in on the day."""

    submissionId = serializers.UUIDField()
    position = serializers.IntegerField(required=False, min_value=1)
    award = serializers.CharField(max_length=_AWARD_CODE_MAX, required=False, allow_null=True, allow_blank=True)


class ReorderRowsRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a reorder body: the complete new order, top to bottom."""

    rowIds = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class AwardRowsRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate the results a jury is saving.

    A list of ``{rowId, award}`` rather than a map, because ``award: null`` has to be
    expressible - clearing a result is an edit a jury makes, and a map with a missing key
    could not tell that apart from "leave this one alone".
    """

    awards = serializers.ListField(
        child=inline_serializer(
            name="ProtocolAwardEntry",
            fields={
                "rowId": serializers.UUIDField(),
                "award": serializers.CharField(max_length=_AWARD_CODE_MAX, allow_null=True, allow_blank=True),
            },
        ),
        allow_empty=False,
    )


class PublishProtocolRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a publish body.

    Both fields are optional and both are decisions made in the publish dialog: which
    columns the page shows, and whether the participants are written to. ``notify`` defaults
    on - a letter is the point of publishing - and is turned off for a re-publication that
    only corrects what the page shows.
    """

    columns = serializers.ListField(child=serializers.ChoiceField(choices=COLUMN_KEYS), required=False, allow_empty=True)
    notify = serializers.BooleanField(required=False, default=True)


#: One column of the protocol table: its stable key and its header.
#:
#: Declared inline because ``label`` is a serializer attribute in DRF, and the wire
#: contract's field name wins. Built **once** and re-instantiated by
#: :func:`_column_schema`: ``inline_serializer`` mints a fresh class per call, and three
#: fields sharing one component name but not one class is how a schema ends up with three
#: incompatible definitions of the same object.
_ColumnResourceSerializer = inline_serializer(
    name="ProtocolColumnResource",
    fields={"key": serializers.CharField(), "label": serializers.CharField()},
).__class__


def _column_schema(*, many: bool = False) -> serializers.BaseSerializer[dict[str, object]]:
    """The column component, as one object or as a list of them."""
    return _ColumnResourceSerializer(many=many)


def _award_option_schema() -> serializers.BaseSerializer[dict[str, object]]:
    """The award vocabulary as the jury's dropdown receives it.

    Served rather than hard-coded in the client so adding an award stays a backend change:
    the wording of "Лауреат I степени" appears on a protocol, on a diploma and in a letter,
    and one of those disagreeing with the others is the bug this prevents.
    """
    return inline_serializer(
        name="ProtocolAwardOption",
        fields={
            "value": serializers.CharField(max_length=_AWARD_CODE_MAX),
            "label": serializers.CharField(),
            "seniority": serializers.IntegerField(),
        },
        many=True,
    )


class ProtocolRowResourceSerializer(serializers.Serializer[dict[str, object]]):
    """One row of the jury's table: the act, and what it won."""

    id = serializers.UUIDField()
    number = serializers.IntegerField()
    submissionId = serializers.UUIDField()
    title = serializers.CharField()
    award = serializers.CharField(max_length=_AWARD_CODE_MAX, allow_null=True)
    awardLabel = serializers.CharField(allow_null=True)
    participants = serializers.ListField(child=serializers.CharField())
    teachers = serializers.ListField(child=serializers.CharField())
    nomination = serializers.CharField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    ageCategory = serializers.CharField(allow_null=True)
    participantGroup = serializers.CharField(allow_null=True)
    participationFormat = serializers.CharField(allow_null=True)
    organization = serializers.CharField(allow_null=True)
    #: True when the entry behind this row is gone from Applications entirely.
    missingPerformance = serializers.BooleanField()


class ProtocolDetailSerializer(serializers.Serializer[dict[str, object]]):
    """One protocol in full: its rows, its results and its publication state."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    nominationId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    competitionTitle = serializers.CharField(allow_null=True)
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=PROTOCOL_STATUS_VALUES)
    rows = ProtocolRowResourceSerializer(many=True)
    availableColumns = _column_schema(many=True)
    publicColumns = _column_schema(many=True)
    awardOptions = _award_option_schema()
    revision = serializers.IntegerField()
    slug = serializers.CharField(allow_null=True)
    path = serializers.CharField(allow_null=True)
    publishedAt = serializers.DateTimeField(allow_null=True)
    #: True when the table has been edited since the revision that is currently public.
    hasUnpublishedChanges = serializers.BooleanField()
    seededFromProgramId = serializers.UUIDField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()
    version = serializers.IntegerField()


class ProtocolSummarySerializer(serializers.Serializer[dict[str, object]]):
    """A protocol as the list of a competition's protocols shows it."""

    id = serializers.UUIDField()
    competitionId = serializers.UUIDField()
    nominationId = serializers.UUIDField()
    nomination = serializers.CharField(allow_null=True)
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=PROTOCOL_STATUS_VALUES)
    rowCount = serializers.IntegerField()
    decidedCount = serializers.IntegerField()
    revision = serializers.IntegerField()
    slug = serializers.CharField(allow_null=True)
    path = serializers.CharField(allow_null=True)
    publishedAt = serializers.DateTimeField(allow_null=True)
    hasUnpublishedChanges = serializers.BooleanField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class PublicationResultSerializer(serializers.Serializer[dict[str, object]]):
    """What one publication did: the protocol, plus what it issued and sent.

    The counts are what the confirmation shows. ``diplomasMissing`` is the one an organizer
    must not miss: those participants have a result and no document, which normally means
    the nomination has no diploma template assigned yet.
    """

    protocol = ProtocolDetailSerializer()
    diplomasAwarded = serializers.IntegerField()
    diplomasCreated = serializers.IntegerField()
    diplomasMissing = serializers.IntegerField()
    lettersSent = serializers.IntegerField()
    lettersSkipped = serializers.IntegerField()


class ProtocolCandidateSerializer(serializers.Serializer[dict[str, object]]):
    """A competing act of this nomination that has no row in the protocol yet."""

    submissionId = serializers.UUIDField()
    title = serializers.CharField()
    nomination = serializers.CharField(allow_null=True)
    discipline = serializers.CharField(allow_null=True)
    ageCategory = serializers.CharField(allow_null=True)
    participantGroup = serializers.CharField(allow_null=True)
    participationFormat = serializers.CharField(allow_null=True)
    participants = serializers.ListField(child=serializers.CharField())
    teachers = serializers.ListField(child=serializers.CharField())
    organization = serializers.CharField(allow_null=True)


# RFC 9457 Problem Details (API-000 §8). Declared inline because ``instance`` is a
# serializer attribute in DRF, and the wire contract's field name wins.
ProtocolProblemDetailSerializer = inline_serializer(
    name="ProtocolProblemDetail",
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
