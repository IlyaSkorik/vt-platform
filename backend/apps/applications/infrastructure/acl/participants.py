"""``DjangoParticipantGuardianRegistry`` — the ACL over the Participants context.

Reads the guardian-link rows directly (an infrastructure-to-infrastructure read
edge, which is what an ACL adapter is for) so the Applications context can answer
"does this performer have a verified parent or guardian on file" without importing
the Participant aggregate or learning its relationship model.

Only ``ACTIVE`` links count. A ``PROPOSED`` link is an unverified claim and a
``REVOKED`` one is a former relationship — treating either as satisfying the
competition's requirement would defeat the point of asking.
"""

from __future__ import annotations

from uuid import UUID

from apps.participants.domain.value_objects import RelationshipStatus
from apps.participants.infrastructure.models.guardian_link import GuardianLinkModel

__all__ = ["DjangoParticipantGuardianRegistry"]


class DjangoParticipantGuardianRegistry:
    """Participants ACL implementing the ``ParticipantGuardianRegistry`` port."""

    def participants_without_active_guardian(self, *, participant_ids: frozenset[str]) -> frozenset[str]:
        """Return the ids among ``participant_ids`` that lack an active guardian link."""
        if not participant_ids:
            return frozenset()

        # Ids reach this context as opaque strings; anything unparseable cannot match
        # a row, so it belongs in the "missing" answer rather than crashing a submit.
        parsed: dict[UUID, str] = {}
        malformed: set[str] = set()
        for raw in participant_ids:
            try:
                parsed[UUID(raw)] = raw
            except (ValueError, AttributeError, TypeError):
                malformed.add(raw)

        covered = set(
            GuardianLinkModel.objects.filter(
                participant_id__in=parsed.keys(),
                status=RelationshipStatus.ACTIVE.value,
            ).values_list("participant_id", flat=True)
        )
        missing = {raw for uuid_value, raw in parsed.items() if uuid_value not in covered}
        return frozenset(missing | malformed)
