"""How many people the platform actually holds.

Three counts the operator wants before any question about money: how many personal
cabinets have been registered, how many participants sit in the registries behind
them, and how many teachers. They answer "is the platform growing", which the
application funnel cannot — a cabinet that never applied to anything is invisible
in every figure the dashboard reports.

Platform-wide by construction, and deliberately outside the dashboard's
organization/competition filters: a cabinet belongs to a person, not to a festival,
so narrowing these to one organizer would answer a different question. That is also
why they are served by their own endpoint rather than folded into the dashboard
payload, where a filter on screen would silently not apply to them.

Reads three contexts' tables directly from the presentation layer, the same
pragmatic seam :mod:`apps.platform.presentation.api.v1.read_models` documents: this
is a reporting projection over data Identity, Participants and the Teacher
Directory each own, kept where its coupling is visible. Every figure is a
``COUNT(*)`` — nothing is loaded to be counted in Python.

Soft-deleted rows are excluded throughout: an erased account is not a cabinet the
platform has.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.identity.infrastructure.models import UserModel
from apps.participants.infrastructure.models import ParticipantRegistryModel
from apps.teachers.domain.value_objects import TeacherStatus
from apps.teachers.infrastructure.models import TeacherModel

__all__ = ["AudienceView", "build_audience"]


@dataclass(frozen=True, slots=True)
class AudienceView:
    """The platform's head counts, each with the subset worth naming beside it.

    The subsets are reported rather than subtracted: "340 участников, 12 из них в
    архиве" is one fact the operator can act on, while a pre-netted 328 hides both
    halves of it.
    """

    cabinets: int
    #: Cabinets whose owner confirmed their e-mail — the ones that can actually be
    #: signed into and written to.
    verified_cabinets: int
    participants: int
    archived_participants: int
    teachers: int
    archived_teachers: int


def build_audience() -> AudienceView:
    """Count cabinets, registry participants and teachers across the whole platform."""
    cabinets = UserModel.objects.filter(deleted_at__isnull=True)
    participants = ParticipantRegistryModel.objects.filter(deleted_at__isnull=True)
    teachers = TeacherModel.objects.filter(deleted_at__isnull=True)
    return AudienceView(
        cabinets=cabinets.count(),
        verified_cabinets=cabinets.filter(email_verified_at__isnull=False).count(),
        # Archived participants stay in the registry (past applications refer to
        # them), so they are counted in the total and named separately.
        participants=participants.count(),
        archived_participants=participants.filter(archived=True).count(),
        teachers=teachers.count(),
        archived_teachers=teachers.filter(status=TeacherStatus.ARCHIVED.value).count(),
    )
