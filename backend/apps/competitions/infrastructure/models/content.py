"""Content child rows of the :class:`Competition` aggregate.

Persistence only (ARCH-001 §7.2, §14): the competition's regulations, documents,
additional services, contacts and public information blocks — content rather than
admissibility configuration — as tables keyed to their competition by foreign key.
The repository synchronizes them with the root as one aggregate.
"""

from __future__ import annotations

from django.db import models

from apps.competitions.domain.value_objects import (
    ContactType,
    Currency,
    DocumentCategory,
    DocumentVisibility,
    RichTextFormat,
)

from .base import BasePersistenceModel

__all__ = [
    "AdditionalServiceModel",
    "ContactModel",
    "DocumentModel",
    "InformationBlockModel",
    "RegulationModel",
]

_DOC_CATEGORY_CHOICES = [(c.value, c.name.title()) for c in DocumentCategory]
_DOC_VISIBILITY_CHOICES = [(v.value, v.name.title()) for v in DocumentVisibility]
_CONTACT_TYPE_CHOICES = [(t.value, t.name.title()) for t in ContactType]
_CURRENCY_CHOICES = [(c.value, c.value) for c in Currency]
_RICH_TEXT_FORMAT_CHOICES = [(f.value, f.name.title()) for f in RichTextFormat]


class RegulationModel(BasePersistenceModel):
    """Database row for a published regulation version (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="regulations",
    )
    title = models.CharField(max_length=200)
    document_version = models.CharField(max_length=50)
    publication_date = models.DateField()
    file_reference = models.CharField(max_length=1024)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_regulation"
        verbose_name = "regulation"
        verbose_name_plural = "regulations"

    def __str__(self) -> str:
        return f"{self.title} ({self.document_version})"


class DocumentModel(BasePersistenceModel):
    """Database row for an organizer-uploaded document (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=32, choices=_DOC_CATEGORY_CHOICES)
    visibility = models.CharField(max_length=16, choices=_DOC_VISIBILITY_CHOICES)
    file_reference = models.CharField(max_length=1024)
    description = models.TextField(null=True, blank=True, default=None)
    sort_order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=False)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_document"
        verbose_name = "document"
        verbose_name_plural = "documents"

    def __str__(self) -> str:
        return self.title


class AdditionalServiceModel(BasePersistenceModel):
    """Database row for an optional paid service (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="additional_services",
    )
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=_CURRENCY_CHOICES, default=Currency.RUB.value)
    description = models.TextField(null=True, blank=True, default=None)
    enabled = models.BooleanField(default=True)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_additional_service"
        verbose_name = "additional service"
        verbose_name_plural = "additional services"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="competitions_service_amount_non_negative"),
        ]

    def __str__(self) -> str:
        return self.name


class ContactModel(BasePersistenceModel):
    """Database row for an official competition contact (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    contact_type = models.CharField(max_length=16, choices=_CONTACT_TYPE_CHOICES)
    value = models.CharField(max_length=500)
    is_primary = models.BooleanField(default=False)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_contact"
        verbose_name = "contact"
        verbose_name_plural = "contacts"

    def __str__(self) -> str:
        return f"{self.contact_type}:{self.value}"


class InformationBlockModel(BasePersistenceModel):
    """Database row for a public-information block (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="information_blocks",
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, default="")
    content_format = models.CharField(max_length=16, choices=_RICH_TEXT_FORMAT_CHOICES, default=RichTextFormat.PLAIN.value)
    published = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_information_block"
        verbose_name = "information block"
        verbose_name_plural = "information blocks"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["competition", "title"], name="competitions_unique_information_block_title"),
        ]

    def __str__(self) -> str:
        return self.title
