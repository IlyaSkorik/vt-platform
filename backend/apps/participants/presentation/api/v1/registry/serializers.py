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
    #: A reference to a stored file, minted by the avatar upload endpoint — not the
    #: image itself. `max_length` is what enforces that: an inline `data:` URL is
    #: orders of magnitude longer, and this field used to accept one, which is how
    #: photographs ended up inline in a text column instead of in the bucket.
    avatarUrl = serializers.CharField(max_length=1024, required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    organizations = ParticipantOrganizationLinkSerializer(many=True)
    #: The legal representative's consent from the Identity journal. Optional on the
    #: wire so an update need not resend it; creation refuses without it (see the view).
    consentId = serializers.UUIDField(required=False, allow_null=True)
    consentVersion = serializers.CharField(max_length=40, required=False, allow_null=True)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Refuse half a consent reference — it is evidence or it is nothing."""
        has_id = attrs.get("consentId") is not None
        has_version = attrs.get("consentVersion") not in (None, "")
        if has_id != has_version:
            raise serializers.ValidationError({"consentVersion": "Согласие передаётся вместе с его версией."})
        return attrs


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
