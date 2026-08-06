"""``UserConsentModel`` — persistence for a versioned consent record.

CONSENT owned/granted by USER_ACCOUNT (DIA-001 §4.1, §5.1;
``USER_ACCOUNT ||--o{ CONSENT``). A first-class, versioned, auditable record
(DATA-001 §4.1; lifecycle Requested → Granted → Active → Withdrawn / Expired →
Superseded). Persistence only — ``ConsentPolicy`` owns the currency/expiry rules.

The subject participant lives in the **Participants** context, so it is held by
identity (``subject_participant_id`` UUID) rather than a cross-context foreign key
(ARCH-001 §9.2).
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["ConsentStatus", "ConsentType", "UserConsentModel"]


class ConsentType(models.TextChoices):
    """The legal basis a consent record covers (mirrors DATA-001 §4.1 wire values)."""

    TERMS_OF_SERVICE = "terms_of_service", "Terms of Service"
    PRIVACY_POLICY = "privacy_policy", "Privacy Policy"
    DATA_PROCESSING = "data_processing", "Data Processing"
    MINOR_DATA_PROCESSING = "minor_data_processing", "Minor Data Processing"
    THIRD_PARTY_DATA_PROCESSING = "third_party_data_processing", "Third-Party Data Processing"
    MARKETING = "marketing", "Marketing"


class ConsentStatus(models.TextChoices):
    """Consent lifecycle states (DATA-001 §4.1)."""

    REQUESTED = "requested", "Requested"
    GRANTED = "granted", "Granted"
    ACTIVE = "active", "Active"
    WITHDRAWN = "withdrawn", "Withdrawn"
    EXPIRED = "expired", "Expired"
    SUPERSEDED = "superseded", "Superseded"


class UserConsentModel(BasePersistenceModel):
    """Database row for one consent grant (persistence only)."""

    user = models.ForeignKey(
        "identity.UserModel",
        on_delete=models.CASCADE,
        related_name="consents",
    )
    consent_type = models.CharField(max_length=32, choices=ConsentType.choices, default=ConsentType.TERMS_OF_SERVICE)
    consent_version = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=ConsentStatus.choices, default=ConsentStatus.REQUESTED)
    # Cross-context reference (Participants) held by identity, never a FK.
    subject_participant_id = models.UUIDField(null=True, blank=True, default=None)
    purpose = models.CharField(max_length=255, null=True, blank=True, default=None)
    granted_at = models.DateTimeField(null=True, blank=True, default=None)
    expires_at = models.DateTimeField(null=True, blank=True, default=None)
    withdrawn_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "identity_user_consent"
        verbose_name = "consent"
        verbose_name_plural = "consents"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["subject_participant_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=ConsentStatus.values),
                name="identity_consent_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(consent_type__in=ConsentType.values),
                name="identity_consent_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"consent {self.consent_type} v{self.consent_version} ({self.status})"
