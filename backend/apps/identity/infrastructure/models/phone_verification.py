"""``UserPhoneVerificationModel`` — persistence for one-time SMS phone verification.

USER_ACCOUNT-owned phone verification (DATA-001 §4.1, IDN-002; lifecycle
Requested → Sent → Verified → Expired). Persistence only: the code lifetime,
resend cooldown, and attempt budget live in ``PhoneVerificationPolicy`` and the
application layer, never here.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["PhoneVerificationStatus", "UserPhoneVerificationModel"]


class PhoneVerificationStatus(models.TextChoices):
    """Phone-verification lifecycle states (DATA-001 §4.1: Requested→Sent→Verified→Expired)."""

    REQUESTED = "requested", "Requested"
    SENT = "sent", "Sent"
    VERIFIED = "verified", "Verified"
    EXPIRED = "expired", "Expired"


class UserPhoneVerificationModel(BasePersistenceModel):
    """Database row for one phone-verification attempt (persistence only)."""

    user = models.ForeignKey(
        "identity.UserModel",
        on_delete=models.CASCADE,
        related_name="phone_verifications",
    )
    phone = models.CharField(max_length=16)
    code = models.CharField(max_length=10)
    status = models.CharField(
        max_length=16,
        choices=PhoneVerificationStatus.choices,
        default=PhoneVerificationStatus.REQUESTED,
    )
    attempts = models.PositiveIntegerField(default=0)
    issued_at = models.DateTimeField(null=True, blank=True, default=None)
    expires_at = models.DateTimeField(null=True, blank=True, default=None)
    verified_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "identity_user_phone_verification"
        verbose_name = "phone verification"
        verbose_name_plural = "phone verifications"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["phone"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=PhoneVerificationStatus.values),
                name="identity_phone_verif_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"phone verification {self.id} ({self.status})"
