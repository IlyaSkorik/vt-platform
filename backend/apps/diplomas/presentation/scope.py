"""Which templates, assignments and paperwork a staff caller may reach.

The platform hosts several organizations, so everything in the Diplomas workspace
is scoped: a template library, the assignments built on it, the registry, the print
packages and the generation archive all belong to one organization and are invisible
to the others. Who the caller is scoped to is the Organization context's answer
(:mod:`apps.organization.presentation.scope`); what follows from it here is this
module.

**Why a :class:`Scope` object rather than a nullable organization id.** There are
three answers, not two — "this one organization", "every organization" (the platform
operator) and "none at all" (an authenticated caller who is staff of nobody) — and
the last two are opposites. Passed as ``uuid | None`` they collapse: ``None`` reads
as both "unscoped" and "no organization", so one forgotten branch turns the
tightest case into the widest one. That is the exact shape of the bug this module
exists to fix, so the type names every state instead, and :meth:`Scope.apply` is
the only way to narrow a queryset.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from rest_framework.request import Request

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.organization.presentation.scope import callers_organization_id, is_platform_operator

__all__ = ["Scope", "callers_scope", "competition_organizer_id"]


@dataclass(frozen=True, slots=True)
class Scope:
    """The set of organizations a request may read and write inside.

    Exactly one of the three constructors applies. ``organization_id`` is set only
    by :meth:`for_organization`; the other two carry ``None`` for opposite reasons,
    which is why the flag and not the id decides behaviour.
    """

    organization_id: uuid.UUID | None
    #: True for the platform operator, who is staff of no organization and reads
    #: across all of them.
    everything: bool = False

    @classmethod
    def for_organization(cls, organization_id: uuid.UUID) -> Scope:
        """An organizer, scoped to their own organization."""
        return cls(organization_id=organization_id)

    @classmethod
    def unrestricted(cls) -> Scope:
        """The platform operator: no narrowing at all."""
        return cls(organization_id=None, everything=True)

    @classmethod
    def empty(cls) -> Scope:
        """Staff of no organization: sees nothing rather than everything."""
        return cls(organization_id=None)

    @classmethod
    def already_authorized(cls) -> Scope:
        """Server-side work whose authorization was decided at the edge.

        The same *value* as :meth:`unrestricted` and deliberately not the same name.
        A generation run resolves its own assignments while executing inside one
        competition the view has already refused to open for the wrong caller — and
        the Celery half of it has no request to ask about anyway. Naming that case
        keeps it apart from "this caller is the platform operator" when someone greps
        for what reads unscoped, which is the question an audit actually asks.
        """
        return cls(organization_id=None, everything=True)

    @property
    def sees_nothing(self) -> bool:
        """Whether this scope admits no row at all."""
        return not self.everything and self.organization_id is None

    def apply(self, queryset: Any, *, field: str = "organizer_id") -> Any:
        """Narrow ``queryset`` to what this scope admits.

        ``field`` is the path from the queryset's model to the owning organization —
        ``organizer_id`` on a template, ``template__organizer_id`` from an assignment.
        """
        if self.everything:
            return queryset
        if self.organization_id is None:
            # Not a no-op. An authenticated caller who is staff of nobody must see
            # an empty library, and returning the queryset untouched here would hand
            # them every organization's.
            return queryset.none()
        return queryset.filter(**{field: self.organization_id})

    def admits(self, organizer_id: uuid.UUID | None) -> bool:
        """Whether a row owned by ``organizer_id`` is inside this scope.

        For the guards that answer before doing any work, where there is no queryset
        to narrow — reaching one template by id, or one competition.
        """
        if self.everything:
            return True
        if self.organization_id is None or organizer_id is None:
            return False
        return self.organization_id == organizer_id


def callers_scope(request: Request) -> Scope:
    """The scope this request acts inside.

    The operator is checked first: they are staff of no organization, so asking
    about membership would put them in :meth:`Scope.empty` — the opposite of what
    they are entitled to.
    """
    if is_platform_operator(request):
        return Scope.unrestricted()
    organization_id = callers_organization_id(request)
    if organization_id is None:
        return Scope.empty()
    return Scope.for_organization(organization_id)


def competition_organizer_id(competition_id: uuid.UUID | str) -> uuid.UUID | None:
    """Who runs this competition, or ``None`` if there is no such competition.

    An id-only cross-context read straight to the Competitions ORM, which is how
    this context already resolves competition labels (ARCH-001 §7.2). ``None`` is
    deliberately indistinguishable from "belongs to someone else" at the call sites:
    both are refused, and telling them apart would let a caller probe which
    competition ids exist.
    """
    return CompetitionModel.objects.filter(id=competition_id, deleted_at__isnull=True).values_list("organizer_id", flat=True).first()
