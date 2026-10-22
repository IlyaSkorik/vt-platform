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
    UpdateContactsConfigHandler,
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
    AddParticipationFormatHandler,
    RemoveParticipationFormatHandler,
    UpdateParticipationFormatHandler,
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
from .landing import UpdateLandingConfigHandler
from .lifecycle import (
    CompleteCompetitionHandler,
    LockSubmissionEditingHandler,
    MarkCompetitionConfiguredHandler,
    MarkCompetitionReadyHandler,
    PublishCompetitionHandler,
    RevertCompetitionToConfiguredHandler,
    RevertCompetitionToDraftHandler,
    StartCompetitionHandler,
    UnlockSubmissionEditingHandler,
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
    DisableNominationWaitlistHandler,
    EnableNominationWaitlistHandler,
    RemoveAgeCategoryHandler,
    RemoveCategoryHandler,
    RemoveDisciplineHandler,
    RemoveParticipantGroupHandler,
    RenameCategoryHandler,
    RenameDisciplineHandler,
    ResumeNominationRegistrationHandler,
    ScheduleNominationRegistrationHandler,
    StopNominationRegistrationHandler,
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
    "AddParticipationFormatHandler",
    "AddPricingRuleHandler",
    "AddRegulationHandler",
    "ChangePriceHandler",
    "CompleteCompetitionHandler",
    "CreateCompetitionHandler",
    "DisableAdditionalServiceHandler",
    "DisableNominationWaitlistHandler",
    "EnableAdditionalServiceHandler",
    "EnableNominationWaitlistHandler",
    "GetCompetitionHandler",
    "HideInformationBlockHandler",
    "ListCompetitionsHandler",
    "LockSubmissionEditingHandler",
    "MakeRegulationCurrentHandler",
    "MarkCompetitionConfiguredHandler",
    "MarkCompetitionReadyHandler",
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
    "RemoveParticipationFormatHandler",
    "RemovePricingRuleHandler",
    "RemoveRegulationHandler",
    "RenameCategoryHandler",
    "RenameDisciplineHandler",
    "ResumeNominationRegistrationHandler",
    "RevertCompetitionToConfiguredHandler",
    "RevertCompetitionToDraftHandler",
    "ScheduleNominationRegistrationHandler",
    "SetPrimaryContactHandler",
    "StartCompetitionHandler",
    "StopNominationRegistrationHandler",
    "UnlockSubmissionEditingHandler",
    "UnpublishDocumentHandler",
    "UpdateAdditionalServiceHandler",
    "UpdateAgeCategoryHandler",
    "UpdateCompetitionBrandingHandler",
    "UpdateCompetitionDeadlinesHandler",
    "UpdateCompetitionGeneralInformationHandler",
    "UpdateCompetitionSettingsHandler",
    "UpdateContactsConfigHandler",
    "UpdateDocumentHandler",
    "UpdateInformationBlockHandler",
    "UpdateLandingConfigHandler",
    "UpdateParticipantGroupHandler",
    "UpdateParticipationFormatHandler",
]
