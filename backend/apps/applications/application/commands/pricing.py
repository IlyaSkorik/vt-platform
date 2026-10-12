"""Pricing use case: calculate and freeze the submission's price snapshot."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import CalculatePriceCommand
from apps.applications.application.exceptions import (
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

from ._support import ensure_owner, ensure_submission_editable, load_submission, parse_submission_id, parse_user_id

__all__ = ["CalculatePriceHandler"]


class CalculatePriceHandler:
    """Use case: price the performance combination and freeze an immutable snapshot.

    The Competition owns pricing: this use case asks the catalog for the list-price
    quote of the performance's combination, applies the calculation type (per
    participant or fixed per performance), and hands the total to the domain to
    freeze. The domain forbids replacing the snapshot once the submission leaves
    the editable states.

    A combination the competition never priced is left unpriced, not rejected -
    pricing is optional, per combination.
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
        ensure_submission_editable(catalog=self._catalog, submission=submission, now=now)

        performance = submission.performance
        if performance is None:
            raise SubmissionStateConflictError(
                "Стоимость считается после того, как выступление заполнено.",
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
            # Pricing is optional: a festival may charge for nothing, or price only some
            # of what it admits. An unpriced combination is not an error - the submission
            # stays unpriced, contributes nothing to the order total, and is submittable
            # as it is. The wizard re-prices on every edit, so this is the ordinary path
            # for a free festival rather than an exceptional one.
            return SubmissionOperationResultDto.of(submission, ())

        total = quote.total_for(submission.participant_count)
        snapshot = PriceSnapshot(price=total, calculated_at=now)
        with translate_domain_errors():
            domain_events = submission.set_price_snapshot(price_snapshot=snapshot, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
