from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = [
    "EducationalOrganizationModel",
    "ParticipantOrganizationMembershipModel",
    "ParticipantRegistryModel",
]


class ParticipantRegistryModel(BasePersistenceModel):
    owner_id = models.UUIDField()
    participant_type = models.CharField(max_length=16, default="solo")
    collective_name = models.CharField(max_length=255, null=True, blank=True, default=None)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True, default=None)
    birth_date = models.DateField()
    gender = models.CharField(max_length=32)
    avatar_url = models.TextField(null=True, blank=True, default=None)
    notes = models.TextField(blank=True, default="")
    archived = models.BooleanField(default=False)

    class Meta(BasePersistenceModel.Meta):
        db_table = "participants_registry"
        verbose_name = "participant registry entry"
        verbose_name_plural = "participant registry entries"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["owner_id"]),
            models.Index(fields=["first_name"]),
            models.Index(fields=["last_name"]),
            models.Index(fields=["birth_date"]),
            models.Index(fields=["gender"]),
            models.Index(fields=["archived"]),
        ]


class EducationalOrganizationModel(BasePersistenceModel):
    owner_id = models.UUIDField()
    name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=64)
    country = models.CharField(max_length=100, null=True, blank=True, default=None)
    city = models.CharField(max_length=100, null=True, blank=True, default=None)
    address = models.CharField(max_length=255, null=True, blank=True, default=None)
    website = models.URLField(max_length=500, null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "participants_educational_organization"
        verbose_name = "educational organization"
        verbose_name_plural = "educational organizations"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["owner_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["city"]),
            models.Index(fields=["organization_type"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["owner_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="participants_unique_owner_org_name",
            ),
        ]


class ParticipantOrganizationMembershipModel(BasePersistenceModel):
    participant = models.ForeignKey(
        ParticipantRegistryModel,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    organization = models.ForeignKey(
        EducationalOrganizationModel,
        on_delete=models.CASCADE,
        related_name="participant_memberships",
    )
    is_primary = models.BooleanField(default=False)

    class Meta(BasePersistenceModel.Meta):
        db_table = "participants_registry_organization_membership"
        verbose_name = "participant organization membership"
        verbose_name_plural = "participant organization memberships"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["participant"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["is_primary"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["participant", "organization"],
                name="participants_unique_registry_org_membership",
            ),
        ]
