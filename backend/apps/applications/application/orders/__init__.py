"""Application (order) use cases for the Applications bounded context.

Handlers that orchestrate the :class:`Application` aggregate together with the
existing :class:`Submission` use cases and the Competition / Institutions ACLs. The
order is the wizard's entry point; these handlers are the thin orchestration seam
between the HTTP edge and the two aggregates.
"""

from apps.applications.application.orders.commands import (
    AddSubmissionToApplicationHandler,
    AutoCancelUnpaidApplicationHandler,
    CancelApplicationHandler,
    CompleteApplicationHandler,
    CreateApplicationHandler,
    MarkApplicationPaidHandler,
    RecordConsentsHandler,
    RemoveAdditionalServiceHandler,
    RemoveSubmissionFromApplicationHandler,
    RequestApplicationPaymentHandler,
    SelectAdditionalServiceHandler,
    SelectEducationalOrganizationHandler,
    SubmitApplicationHandler,
    SyncApplicationHandler,
    UploadApplicationReceiptHandler,
)
from apps.applications.application.orders.queries import (
    GetApplicationHandler,
    ListApplicationsHandler,
    ListDraftApplicationsHandler,
)

__all__ = [
    "AddSubmissionToApplicationHandler",
    "AutoCancelUnpaidApplicationHandler",
    "CancelApplicationHandler",
    "CompleteApplicationHandler",
    "CreateApplicationHandler",
    "GetApplicationHandler",
    "ListApplicationsHandler",
    "ListDraftApplicationsHandler",
    "MarkApplicationPaidHandler",
    "RecordConsentsHandler",
    "RemoveAdditionalServiceHandler",
    "RemoveSubmissionFromApplicationHandler",
    "RequestApplicationPaymentHandler",
    "SelectAdditionalServiceHandler",
    "SelectEducationalOrganizationHandler",
    "SubmitApplicationHandler",
    "SyncApplicationHandler",
    "UploadApplicationReceiptHandler",
]
