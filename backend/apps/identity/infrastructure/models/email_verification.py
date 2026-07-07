"""``UserEmailVerificationModel`` — persistence for email-ownership verification.

The "Email Verification" business object owned by USER_ACCOUNT (DATA-001 §4.1,
lifecycle Requested → Sent → Verified → Expired; IDN-002). Persistence only: the
verification/resend rules live in ``EmailVerificationPolicy`` and the application
layer, never here.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["EmailVerificationStatus", "UserEmailVerificationModel"]


class EmailVerificationStatus(models.TextChoices):
    """Email-verification lifecycle states (DATA-001 §4.1: Requested→Sent→Verified→Expired)."""

    REQUESTED = "requested", "Requested"
    SENT = "sent", "Sent"
    VERIFIED = "verified", "Verified"
    EXPIRED = "expired", "Expired"


class UserEmailVerificationModel(BasePersistenceModel):
    """Database row for one email-verification attempt (persistence only)."""

    user = models.ForeignKey(
        "identity.UserModel",
        on_delete=models.CASCADE,
        related_name="email_verifications",
    )
    email = models.EmailField(max_length=320)
    token = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=EmailVerificationStatus.choices,
        default=EmailVerificationStatus.REQUESTED,
    )
    resend_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True, default=None)
    expires_at = models.DateTimeField(null=True, blank=True, default=None)
    verified_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "identity_user_email_verification"
        verbose_name = "email verification"
        verbose_name_plural = "email verifications"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["email"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["token"], name="identity_email_verif_unique_token"),
            models.CheckConstraint(
                condition=models.Q(status__in=EmailVerificationStatus.values),
                name="identity_email_verif_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"email verification {self.id} ({self.status})"
