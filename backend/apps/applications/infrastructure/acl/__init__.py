"""Anti-corruption adapters: read models over sibling bounded contexts.

Infrastructure-layer gateways that implement the application ACL ports by reading
the Competition, Identity and Participants contexts. Only these adapters know the
foreign contexts; the domain and application layers stay decoupled.
"""

from __future__ import annotations

from .competition import DjangoCompetitionCatalog, DjangoCompetitionServiceCatalog
from .educational_organizations import DjangoEducationalOrganizationDirectory
from .identity import DjangoIdentityReadModel
from .organization import DjangoOrganizationReadModel
from .upload_policy import DjangoCompetitionUploadPolicy

__all__ = [
    "DjangoCompetitionCatalog",
    "DjangoCompetitionServiceCatalog",
    "DjangoCompetitionUploadPolicy",
    "DjangoEducationalOrganizationDirectory",
    "DjangoIdentityReadModel",
    "DjangoOrganizationReadModel",
]
