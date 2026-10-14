"""``DjangoOrganizationReadModel`` - the ACL over the Organization (staff) context.

Answers the two authorization questions the Submission use cases need - does a user
hold staff permission, and may a reviewer act on submissions - by reusing the
Organization context's staff-membership read service (the same seam ``/users/me``
and the Competitions edge use). No role logic is duplicated here.
"""

from __future__ import annotations

from apps.applications.domain.value_objects import ReviewerId, UserId
from apps.organization.composition import build_staff_membership_read_service
from apps.platform.composition import build_platform_access_read_service

__all__ = ["DjangoOrganizationReadModel"]


class DjangoOrganizationReadModel:
    """Organization ACL implementing the ``OrganizationReadModel`` port."""

    def has_staff_permission(self, *, user_id: UserId) -> bool:
        """Whether ``user_id`` holds an active staff membership."""
        return build_staff_membership_read_service().active_for_user(user_id.value) is not None

    def can_review_submissions(self, *, reviewer_id: ReviewerId) -> bool:
        """Whether ``reviewer_id`` may review submissions.

        Any active staff member may - and so may the platform operator, who is staff
        of no organization by design (see
        :mod:`apps.organization.presentation.scope`). Without this they were the one
        caller who could open «Обработка заявок» and find the рабочая карточка empty:
        the queue is scoped at the edge and let them in, then every read of the
        selected entry was refused here, which reads on screen as «выберите заявку из
        очереди» for an entry already selected.

        Letting them through here does not widen which organizations they may work
        in: the organizer endpoints are gated by ``IsOrganizationStaff``, which asks
        an operator to name the organization they have stepped into before anything
        is read at all. This answers the second question - may this person act as an
        organizer at all - and for the operator the answer was always yes.
        """
        if build_staff_membership_read_service().active_for_user(reviewer_id.value) is not None:
            return True
        return build_platform_access_read_service().is_platform_administrator(reviewer_id.value)
