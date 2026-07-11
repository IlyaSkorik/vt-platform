"""Persistence models for the Competitions bounded context.

Persistence-only Django models (ARCH-001 §7.2, §14): the :class:`CompetitionModel`
aggregate-root row and its child tables (taxonomy, admission/pricing rules, and
content). No business logic lives here — the domain aggregate is authoritative and
the mapper/repository read and write these rows on its behalf.
"""

from __future__ import annotations

from .base import BasePersistenceModel, uuid7
from .competition import CompetitionModel, CompetitionStatusChoices
from .content import (
    AdditionalServiceModel,
    ContactModel,
    DocumentModel,
    InformationBlockModel,
    RegulationModel,
)
from .rules import AdmissionRuleModel, PricingRuleModel
from .taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)

__all__ = [
    "AdditionalServiceModel",
    "AdmissionRuleModel",
    "AgeCategoryModel",
    "BasePersistenceModel",
    "CategoryModel",
    "CompetitionModel",
    "CompetitionStatusChoices",
    "ContactModel",
    "DisciplineModel",
    "DocumentModel",
    "InformationBlockModel",
    "ParticipantGroupModel",
    "ParticipationFormatModel",
    "PricingRuleModel",
    "RegulationModel",
    "uuid7",
]
