"""Domain-event handlers for the Competitions bounded context.

React to events from this and other contexts (ARCH-001 §4.8).
Structure only at bootstrap.
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
)