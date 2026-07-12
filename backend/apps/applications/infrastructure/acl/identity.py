"""``DjangoIdentityReadModel`` - the ACL over the Identity context.

Reads the Identity ``UserModel`` directly (an infrastructure-to-infrastructure read
edge, which is what an ACL adapter is for) so the Applications context can answer
"does this applicant exist / what is their display name" without importing the
Identity aggregate.
"""

from __future__ import annotations

from apps.applications.application.interfaces import ApplicantInfo
from apps.applications.domain.value_objects import UserId
from apps.identity.infrastructure.models.user import UserModel

__all__ = ["DjangoIdentityReadModel"]


class DjangoIdentityReadModel:
    """Identity ACL implementing the ``IdentityReadModel`` port."""

    def exists(self, *, user_id: UserId) -> bool:
        """Whether an Identity user with ``user_id`` exists."""
        return UserModel.objects.filter(pk=user_id.value).exists()

    def get_applicant(self, *, user_id: UserId) -> ApplicantInfo | None:
        """Return the applicant's display information, or ``None`` if unknown."""
        model = UserModel.objects.filter(pk=user_id.value).only("first_name", "last_name", "middle_name", "email").first()
        if model is None:
            return None
        parts = [model.last_name, model.first_name]
        if model.middle_name:
            parts.append(model.middle_name)
        return ApplicantInfo(user_id=user_id.json(), display_name=" ".join(parts), email=model.email)
