"""``DjangoOrganizationReadModel`` - the ACL over the Organization (staff) context.

Answers the two authorization questions the Submission use cases need - does a user
hold staff permission, and may a reviewer act on submissions - by reusing the
Organization context's staff-membership read service (the same seam ``/users/me``
and the Competitions edge use). No role logic is duplicated here.
"""

from __future__ import annotations

from apps.applications.domain.value_objects import ReviewerId, UserId
from apps.organization.composition import build_staff_membership_read_service

__all__ = ["DjangoOrganizationReadModel"]


class DjangoOrganizationReadModel:
    """Organization ACL implementing the ``OrganizationReadModel`` port."""

    def has_staff_permission(self, *, user_id: UserId) -> bool:
        """Whether ``user_id`` holds an active staff membership."""
        return build_staff_membership_read_service().active_for_user(user_id.value) is not None

    def can_review_submissions(self, *, reviewer_id: ReviewerId) -> bool:
        """Whether ``reviewer_id`` may review submissions (any active staff member may)."""
        return build_staff_membership_read_service().active_for_user(reviewer_id.value) is not None
