"""Pricing use case: calculate and freeze the submission's price snapshot."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import CalculatePriceCommand
from apps.applications.application.exceptions import (
    CompetitionClosedError,
    CompetitionCombinationNotFoundError,
    SubmissionStateConflictError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    CompetitionCatalog,
    EventPublisher,
    SubmissionRepository,
)
from apps.applications.domain.value_objects import PriceSnapshot

from ._support import ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = ["CalculatePriceHandler"]


class CalculatePriceHandler:
    """Use case: price the performance combination and freeze an immutable snapshot.

    The Competition owns pricing: this use case asks the catalog for the list-price
    quote of the performance's combination, applies the calculation type (per
    participant or fixed per performance), and hands the total to the domain to
    freeze. The domain forbids replacing the snapshot once the submission leaves
    the editable states.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._events = events

    def handle(self, command: CalculatePriceCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=submission.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")

        performance = submission.performance
        if performance is None:
            raise SubmissionStateConflictError(
                "A performance must be set before the price can be calculated.",
                domain_code="performance_not_set",
            )

        quote = self._catalog.price_quote(
            competition_id=submission.competition_id,
            nomination_id=performance.nomination_id,
            discipline_id=performance.discipline_id,
            age_category_id=performance.age_category_id,
            participant_group_id=performance.participant_group_id,
            participation_format_id=performance.participation_format_id,
        )
        if quote is None:
            raise CompetitionCombinationNotFoundError("The competition has no pricing for this combination.")

        total = quote.total_for(submission.participant_count)
        snapshot = PriceSnapshot(price=total, calculated_at=now)
        with translate_domain_errors():
            domain_events = submission.set_price_snapshot(price_snapshot=snapshot, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
