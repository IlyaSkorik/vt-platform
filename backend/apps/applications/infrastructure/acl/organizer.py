"""``DjangoCompetitionOrganizerDirectory`` - the ACL that answers "who runs this festival".

Implements the :class:`~apps.applications.application.interfaces.
CompetitionOrganizerDirectory` port. The Applications context stores only a
``CompetitionId``; when a letter has to reach the people running that competition,
this adapter resolves it - across three foreign contexts, in the order an organizer
would expect to be reached:

1. the competition's own published contacts (its override mailbox and the named
   people on its team) - the address the organizer chose to publish for *this*
   festival, which is normally the coordinator actually handling applications;
2. the organization's contact mailbox, when the competition says it uses the
   organization's contacts rather than its own;
3. failing both, the mailboxes of the organization's active decision-making staff.

The third step exists because the first two are optional profile fields: an
organization that never filled in a public email would otherwise silently never hear
that an application changed, which is the one outcome this feature exists to prevent.
"""

from __future__ import annotations

from typing import Final

from apps.applications.application.interfaces import OrganizerContacts
from apps.applications.domain.value_objects import CompetitionId
from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.infrastructure.models.user import UserModel
from apps.organization.infrastructure.models.organization import OrganizationModel
from apps.organization.infrastructure.models.staff_membership import (
    MembershipStatusChoices,
    StaffMembershipModel,
    StaffRoleChoices,
)

__all__ = ["DjangoCompetitionOrganizerDirectory"]

#: The staff roles a "your applicant changed their entry" notice is addressed to when
#: no published mailbox exists. Support and content roles are deliberately left out -
#: they cannot act on the change, and the fallback is meant to reach somebody who can.
_RESPONSIBLE_ROLES: Final = (
    StaffRoleChoices.OWNER,
    StaffRoleChoices.DIRECTOR,
    StaffRoleChoices.COMPETITION_MANAGER,
)

#: How many mailboxes one notice may be addressed to. A festival is run by a handful
#: of people; a larger list means a misconfiguration, and sending to all of it would
#: turn one applicant's edit into a mailing.
_MAX_RECIPIENTS: Final = 10


def _clean_email(value: object) -> str | None:
    """Return ``value`` as a plausible email address, or ``None``.

    Deliberately shallow: these fields are free text an organizer typed into a
    profile form, so the only question worth asking is whether handing it to the mail
    layer could possibly work.
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if "@" not in candidate or len(candidate) < 5 or " " in candidate:
        return None
    return candidate


class DjangoCompetitionOrganizerDirectory:
    """Competition/Organization/Identity ACL implementing ``CompetitionOrganizerDirectory``."""

    def get_organizer(self, *, competition_id: CompetitionId) -> OrganizerContacts | None:
        row = (
            CompetitionModel.objects.filter(pk=competition_id.value, deleted_at__isnull=True)
            .values("title", "organizer_id", "contacts_config")
            .first()
        )
        if row is None:
            return None

        contacts = row["contacts_config"] if isinstance(row["contacts_config"], dict) else {}
        organizer_id = str(row["organizer_id"])
        emails = self._published_emails(contacts)
        if not emails and bool(contacts.get("use_organization_contacts", True)):
            emails = self._organization_emails(organizer_id)
        if not emails:
            emails = self._staff_emails(organizer_id)

        return OrganizerContacts(competition_title=str(row["title"]), emails=tuple(emails[:_MAX_RECIPIENTS]))

    @staticmethod
    def _published_emails(contacts: dict[str, object]) -> list[str]:
        """The mailboxes this competition publishes: its override plus its named team."""
        found: list[str] = []
        override = contacts.get("override")
        if isinstance(override, dict):
            candidate = _clean_email(override.get("email"))
            if candidate is not None:
                found.append(candidate)
        team = contacts.get("team_contacts")
        if isinstance(team, list):
            for member in team:
                if not isinstance(member, dict):
                    continue
                candidate = _clean_email(member.get("email"))
                if candidate is not None and candidate not in found:
                    found.append(candidate)
        return found

    @staticmethod
    def _organization_emails(organizer_id: str) -> list[str]:
        """The organization's own contact mailbox, when it has one on file."""
        contact = OrganizationModel.objects.filter(pk=organizer_id, deleted_at__isnull=True).values_list("email", flat=True).first()
        candidate = _clean_email(contact)
        return [] if candidate is None else [candidate]

    @staticmethod
    def _staff_emails(organizer_id: str) -> list[str]:
        """Last resort: the mailboxes of the organization's active responsible staff."""
        user_ids = list(
            StaffMembershipModel.objects.filter(
                organization_id=organizer_id,
                status=MembershipStatusChoices.ACTIVE,
                role__in=[role.value for role in _RESPONSIBLE_ROLES],
                deleted_at__isnull=True,
            ).values_list("user_id", flat=True)[:_MAX_RECIPIENTS]
        )
        if not user_ids:
            return []
        found: list[str] = []
        for address in UserModel.objects.filter(pk__in=user_ids).values_list("email", flat=True):
            candidate = _clean_email(address)
            if candidate is not None and candidate not in found:
                found.append(candidate)
        return found
