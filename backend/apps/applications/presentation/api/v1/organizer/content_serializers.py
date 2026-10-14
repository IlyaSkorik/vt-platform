"""Request shapes for the organizer's correction of a submitted entry.

Every collection is the **whole** desired state of its section, mirroring the form
the organizer is looking at. Sections left out of the body are left alone, which is
what lets a screen that only edits the performance send only the performance.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

_GENDERS = ("MALE", "FEMALE", "OTHER")

#: A collective may name this many people (the aggregate's own ceiling); rejecting a
#: runaway list here keeps a mistyped paste from reaching the domain as 10 000 rows.
_MAX_MEMBERS = 200

#: The aggregate's own ceiling on an institution name, mirrored here so a paste that
#: could never be stored is refused at the edge with a field error rather than a 422.
_MAX_ORGANIZATION_NAME = 255


class OrganizerPerformanceSerializer(serializers.Serializer[dict[str, object]]):
    """The number as the organizer wants it to read."""

    title = serializers.CharField(max_length=200)
    durationSeconds = serializers.IntegerField(min_value=0)
    nominationId = serializers.CharField()
    disciplineId = serializers.CharField()
    ageCategoryId = serializers.CharField()
    participantGroupId = serializers.CharField()
    participationFormatId = serializers.CharField()
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    ageComposition = serializers.CharField(required=False, allow_blank=True, default="")


class OrganizerParticipantSerializer(serializers.Serializer[dict[str, object]]):
    """One performer as the organizer wants it to read.

    ``id`` names an entry already on the submission; without it the performer is a
    new one. A soloist supplies the name parts, a collective its ``displayName`` —
    which is why both are optional here and the pair is checked together.
    """

    id = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    displayName = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    firstName = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    lastName = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    middleName = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    birthDate = serializers.DateField(required=False, allow_null=True, default=None)
    gender = serializers.ChoiceField(choices=_GENDERS, required=False, allow_null=True, allow_blank=True, default=None)
    memberCount = serializers.IntegerField(min_value=1, required=False, default=1)
    members = serializers.ListField(
        child=serializers.CharField(allow_blank=True, max_length=200),
        required=False,
        default=list,
        max_length=_MAX_MEMBERS,
    )
    #: The institution to print for this performer on this entry. Blank withdraws the
    #: correction rather than asserting there is none — see
    #: :class:`~apps.applications.application.dto.commands.OrganizerParticipantInput`.
    organizationName = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
        max_length=_MAX_ORGANIZATION_NAME,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        named = bool((attrs.get("firstName") or "").strip()) and bool((attrs.get("lastName") or "").strip())
        if not named and not (attrs.get("displayName") or "").strip():
            raise serializers.ValidationError("Укажите фамилию и имя участника или название коллектива.")
        return attrs


class OrganizerTeacherSerializer(serializers.Serializer[dict[str, object]]):
    """One credited mentor as the organizer wants it to read."""

    id = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    firstName = serializers.CharField(max_length=120)
    lastName = serializers.CharField(max_length=120)
    middleName = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    role = serializers.CharField(max_length=120)


class OrganizerSubmissionContentSerializer(serializers.Serializer[dict[str, object]]):
    """The correction itself: the sections being rewritten, and why.

    ``comment`` is the organizer's own explanation. It is not required — a surname
    corrected from the applicant's own paperwork explains itself — but when given it
    travels into the letter, because "мы поправили вашу заявку" without a reason is
    the kind of message that generates a phone call.
    """

    performance = OrganizerPerformanceSerializer(required=False)
    participants = serializers.ListField(child=OrganizerParticipantSerializer(), required=False, max_length=200)
    teachers = serializers.ListField(child=OrganizerTeacherSerializer(), required=False, max_length=50)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not any(key in attrs for key in ("performance", "participants", "teachers")):
            raise serializers.ValidationError("Нечего сохранять: не передан ни один раздел заявки.")
        for section in ("participants", "teachers"):
            entries = attrs.get(section) or []
            seen: set[str] = set()
            for entry in entries:
                identifier = (entry.get("id") or "").strip()
                if not identifier:
                    continue
                if identifier in seen:
                    raise serializers.ValidationError("Одна и та же запись передана дважды — обновите страницу.")
                seen.add(identifier)
        return attrs
