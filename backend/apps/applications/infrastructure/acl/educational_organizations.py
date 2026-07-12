"""``DjangoEducationalOrganizationDirectory`` - the ACL over educational organizations.

Resolves an educational-organization reference to its display name by reading the
Participants context's ``EducationalOrganizationModel`` (where the platform's
directory of schools/organizations lives). Only non-archived organizations resolve.
"""

from __future__ import annotations

from apps.applications.application.interfaces import EducationalOrganizationInfo
from apps.applications.domain.value_objects import EducationalOrganizationId
from apps.participants.infrastructure.models import EducationalOrganizationModel

__all__ = ["DjangoEducationalOrganizationDirectory"]


class DjangoEducationalOrganizationDirectory:
    """Institutions/Participants ACL implementing the ``EducationalOrganizationDirectory`` port."""

    def get(self, *, organization_id: EducationalOrganizationId) -> EducationalOrganizationInfo | None:
        """Return the organization's display info, or ``None`` if unknown."""
        model = EducationalOrganizationModel.objects.filter(pk=organization_id.value, deleted_at__isnull=True).only("name").first()
        if model is None:
            return None
        return EducationalOrganizationInfo(organization_id=organization_id.json(), name=model.name)
