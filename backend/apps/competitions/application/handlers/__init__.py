"""Command and query handlers (use cases) for the Competitions bounded context.

Each handler orchestrates a single use case: load the aggregate, invoke one
domain operation, persist, and project a view DTO (ARCH-001 §7.2). This package
is the application layer's public surface — the composition root and the
presentation edge import handlers from here.
"""

from .contacts import (
    AddContactHandler,
    RemoveContactHandler,
    SetPrimaryContactHandler,
)
from .create import CreateCompetitionHandler
from .documents import (
    AddDocumentHandler,
    PublishDocumentHandler,
    RemoveDocumentHandler,
    UnpublishDocumentHandler,
    UpdateDocumentHandler,
)
from .formats import (
    DisableFormatHandler,
    EnableFormatHandler,
)
from .general_information import (
    UpdateCompetitionBrandingHandler,
    UpdateCompetitionDeadlinesHandler,
    UpdateCompetitionGeneralInformationHandler,
    UpdateCompetitionSettingsHandler,
)
from .information import (
    AddInformationBlockHandler,
    HideInformationBlockHandler,
    PublishInformationBlockHandler,
    RemoveInformationBlockHandler,
    UpdateInformationBlockHandler,
)
from .lifecycle import (
    ArchiveCompetitionHandler,
    CloseRegistrationHandler,
    CompleteCompetitionHandler,
    MarkCompetitionConfiguredHandler,
    MarkCompetitionReadyHandler,
    OpenRegistrationHandler,
    PublishCompetitionHandler,
    RevertCompetitionToConfiguredHandler,
    RevertCompetitionToDraftHandler,
    StartCompetitionHandler,
)
from .queries import (
    GetCompetitionHandler,
    ListCompetitionsHandler,
)
from .regulations import (
    AddRegulationHandler,
    MakeRegulationCurrentHandler,
    RemoveRegulationHandler,
)
from .rules import (
    AddAdmissionRuleHandler,
    AddPricingRuleHandler,
    ChangePriceHandler,
    RemoveAdmissionRuleHandler,
    RemovePricingRuleHandler,
)
from .services import (
    AddAdditionalServiceHandler,
    DisableAdditionalServiceHandler,
    EnableAdditionalServiceHandler,
    RemoveAdditionalServiceHandler,
    UpdateAdditionalServiceHandler,
)
from .taxonomy import (
    AddAgeCategoryHandler,
    AddCategoryHandler,
    AddDisciplineHandler,
    AddParticipantGroupHandler,
    RemoveAgeCategoryHandler,
    RemoveCategoryHandler,
    RemoveDisciplineHandler,
    RemoveParticipantGroupHandler,
    RenameCategoryHandler,
    RenameDisciplineHandler,
    UpdateAgeCategoryHandler,
    UpdateParticipantGroupHandler,
)

__all__ = [
    "AddAdditionalServiceHandler",
    "AddAdmissionRuleHandler",
    "AddAgeCategoryHandler",
    "AddCategoryHandler",
    "AddContactHandler",
    "AddDisciplineHandler",
    "AddDocumentHandler",
    "AddInformationBlockHandler",
    "AddParticipantGroupHandler",
    "AddPricingRuleHandler",
    "AddRegulationHandler",
    "ArchiveCompetitionHandler",
    "ChangePriceHandler",
    "CloseRegistrationHandler",
    "CompleteCompetitionHandler",
    "CreateCompetitionHandler",
    "DisableAdditionalServiceHandler",
    "DisableFormatHandler",
    "EnableAdditionalServiceHandler",
    "EnableFormatHandler",
    "GetCompetitionHandler",
    "HideInformationBlockHandler",
    "ListCompetitionsHandler",
    "MakeRegulationCurrentHandler",
    "MarkCompetitionConfiguredHandler",
    "MarkCompetitionReadyHandler",
    "OpenRegistrationHandler",
    "PublishCompetitionHandler",
    "PublishDocumentHandler",
    "PublishInformationBlockHandler",
    "RemoveAdditionalServiceHandler",
    "RemoveAdmissionRuleHandler",
    "RemoveAgeCategoryHandler",
    "RemoveCategoryHandler",
    "RemoveContactHandler",
    "RemoveDisciplineHandler",
    "RemoveDocumentHandler",
    "RemoveInformationBlockHandler",
    "RemoveParticipantGroupHandler",
    "RemovePricingRuleHandler",
    "RemoveRegulationHandler",
    "RenameCategoryHandler",
    "RenameDisciplineHandler",
    "RevertCompetitionToConfiguredHandler",
    "RevertCompetitionToDraftHandler",
    "SetPrimaryContactHandler",
    "StartCompetitionHandler",
    "UnpublishDocumentHandler",
    "UpdateAdditionalServiceHandler",
    "UpdateCompetitionBrandingHandler",
    "UpdateCompetitionDeadlinesHandler",
    "UpdateCompetitionGeneralInformationHandler",
    "UpdateAgeCategoryHandler",
    "UpdateCompetitionSettingsHandler",
    "UpdateDocumentHandler",
    "UpdateInformationBlockHandler",
    "UpdateParticipantGroupHandler",
]
