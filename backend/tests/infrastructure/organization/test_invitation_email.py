"""The invitation letter names the role in the words the panel uses.

``StaffRole`` values are authorization codes. Putting one in a letter ("c ролью
COMPETITION_MANAGER") asks the invitee to read a constant; the panel already calls
that role «Менеджер фестивалей», and the letter must agree with it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.core import mail

from apps.organization.composition import DjangoStaffInvitationEmailGateway
from apps.organization.domain.value_objects import OrganizationName, StaffEmail, StaffRole

EXPIRES = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)


def _send(role: StaffRole) -> mail.EmailMultiAlternatives:
    DjangoStaffInvitationEmailGateway().send_staff_invitation(
        recipient_email=StaffEmail("teammate@example.com"),
        organization_name=OrganizationName("Ромашка"),
        role=role,
        expires_at=EXPIRES,
        token="https://example.test/invite/abc",
    )
    sent = mail.outbox[-1]
    assert isinstance(sent, mail.EmailMultiAlternatives)
    return sent


@pytest.mark.django_db
def test_the_role_is_named_in_russian_in_both_versions_of_the_letter() -> None:
    sent = _send(StaffRole.COMPETITION_MANAGER)
    html = sent.alternatives[0][0]

    assert "«Менеджер фестивалей»" in sent.body
    assert "COMPETITION_MANAGER" not in sent.body
    assert "«Менеджер фестивалей»" in str(html)
    assert "COMPETITION_MANAGER" not in str(html)


@pytest.mark.django_db
def test_every_role_has_a_name_of_its_own() -> None:
    """A role added to the enum without a name would silently mail its code."""
    from apps.organization.composition import _RU_ROLES

    assert set(StaffRole) == set(_RU_ROLES)


@pytest.mark.django_db
def test_the_letter_is_written_in_russian_throughout() -> None:
    sent = _send(StaffRole.OWNER)

    assert sent.body.startswith("Вас пригласили в команду Ромашка с ролью «Владелец».")
