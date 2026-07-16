"""Command use cases for the Applications bounded context.

One use case = one business operation and one transaction boundary
(ARCH-001 §7.2, §7.4). Each handler loads the aggregate through the repository
port, enforces the application-owned preconditions (ownership, organizer
authorization, cross-context existence), delegates every business decision to the
domain, then persists the aggregate and publishes the events the domain produced.
"""

from __future__ import annotations

from .attachments import AttachFileHandler, RemoveAttachmentHandler
from .cancel import CancelSubmissionByReviewerHandler, CancelSubmissionHandler
from .draft import CreateSubmissionHandler, DeleteDraftSubmissionHandler
from .participants import (
    AddParticipantHandler,
    RemoveParticipantHandler,
    UpdateParticipantHandler,
)
from .payment import (
    AcceptSubmissionHandler,
    CompleteSubmissionHandler,
    MarkPaidHandler,
    MarkWaitingPaymentHandler,
    ScheduleSubmissionHandler,
)
from .performance import SetPerformanceHandler, UpdatePerformanceHandler
from .pricing import CalculatePriceHandler
from .review import (
    ApproveSubmissionHandler,
    ReturnSubmissionForCorrectionHandler,
    StartReviewHandler,
    SubmitSubmissionHandler,
)
from .teachers import AddTeacherHandler, RemoveTeacherHandler, UpdateTeacherHandler

__all__ = [
    "AcceptSubmissionHandler",
    "AddParticipantHandler",
    "AddTeacherHandler",
    "ApproveSubmissionHandler",
    "AttachFileHandler",
    "CalculatePriceHandler",
    "CancelSubmissionByReviewerHandler",
    "CancelSubmissionHandler",
    "CompleteSubmissionHandler",
    "CreateSubmissionHandler",
    "DeleteDraftSubmissionHandler",
    "MarkPaidHandler",
    "MarkWaitingPaymentHandler",
    "RemoveAttachmentHandler",
    "RemoveParticipantHandler",
    "RemoveTeacherHandler",
    "ReturnSubmissionForCorrectionHandler",
    "ScheduleSubmissionHandler",
    "SetPerformanceHandler",
    "StartReviewHandler",
    "SubmitSubmissionHandler",
    "UpdateParticipantHandler",
    "UpdatePerformanceHandler",
    "UpdateTeacherHandler",
]
