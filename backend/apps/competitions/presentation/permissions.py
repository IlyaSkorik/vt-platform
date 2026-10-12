"""Authorization for the Competitions REST edge.

Organizer endpoints are staff-only (ARCH-001 §14): the *source of truth* for
"is this user staff?" is the Organization bounded context, consulted through its
published :class:`~apps.organization.application.read_models.StaffMembershipReadService`
read-port. This module is only a thin DRF adapter over that port — it re-implements
no role logic, so authorization stays in one place.
"""

from __future__ import annotations

from apps.organization.presentation.permissions import IsOrganizationStaff as OrganizationStaffPermission

__all__ = ["IsOrganizationStaff"]


class IsOrganizationStaff(OrganizationStaffPermission):
    """Grant access only to users acting for an organization.

    Participants (and any other authenticated non-staff user) are denied. Absence
    of an active membership — the common case — is a plain deny, never an error.

    Subclassed from the Organization context's own rule rather than re-derived
    from the membership read model, which is what this module used to do. The two
    copies drifted the first time "acting for an organization" stopped meaning
    exactly "holds a membership": a platform operator inside somebody's panel was
    staff everywhere on the platform except here. Only the sentence shown to the
    caller is this context's own.
    """

    message = "Organizer endpoints are restricted to organization staff."
