from __future__ import annotations

from rest_framework import serializers


class ParticipantOrganizationLinkSerializer(serializers.Serializer[dict[str, object]]):
    organizationId = serializers.UUIDField()
    isPrimary = serializers.BooleanField()


class ParticipantRegistryWriteSerializer(serializers.Serializer[dict[str, object]]):
    participantType = serializers.ChoiceField(choices=["solo", "collective"], required=False, default="solo")
    collectiveName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    firstName = serializers.CharField(required=False, allow_blank=True)
    lastName = serializers.CharField(required=False, allow_blank=True)
    middleName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    birthDate = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=["female", "male", "other"], required=False, allow_null=True)
    avatarUrl = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    organizations = ParticipantOrganizationLinkSerializer(many=True)


class OrganizationWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField()
    type = serializers.ChoiceField(
        choices=[
            "school",
            "music_school",
            "dance_studio",
            "art_school",
            "college",
            "university",
            "cultural_center",
            "creative_center",
            "private_studio",
            "other",
        ]
    )
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    website = serializers.URLField(required=False, allow_null=True, allow_blank=True)
