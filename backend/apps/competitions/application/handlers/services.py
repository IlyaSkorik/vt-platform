"""Use cases: additional services."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddAdditionalServiceCommand,
    DisableAdditionalServiceCommand,
    EnableAdditionalServiceCommand,
    RemoveAdditionalServiceCommand,
    UpdateAdditionalServiceCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import (
    ParticipationFormatId,
    ServiceBillingModel,
    ServiceDescription,
    ServiceId,
    ServiceName,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddAdditionalServiceHandler",
    "DisableAdditionalServiceHandler",
    "EnableAdditionalServiceHandler",
    "RemoveAdditionalServiceHandler",
    "UpdateAdditionalServiceHandler",
)


def _format_ids(raw: list[str]) -> tuple[ParticipationFormatId, ...]:
    return tuple(ParticipationFormatId.from_string(value) for value in raw)


class AddAdditionalServiceHandler(CompetitionCommandHandler):
    """Add an additional service."""

    def handle(
        self,
        command: AddAdditionalServiceCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.add_additional_service(
            service_id=ServiceId.from_uuid(
                self._uuids.new(),
            ),
            name=ServiceName(
                command.name,
            ),
            price=self._money(
                amount=command.amount,
                currency=command.currency,
            ),
            available_format_ids=_format_ids(command.participation_format_ids),
            billing_model=ServiceBillingModel(command.billing_model),
            description=(ServiceDescription(command.description) if command.description else None),
            required=command.required,
            enabled=command.enabled,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class UpdateAdditionalServiceHandler(CompetitionCommandHandler):
    """Update an additional service."""

    def handle(
        self,
        command: UpdateAdditionalServiceCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.update_additional_service(
            service_id=ServiceId.from_string(
                command.service_id,
            ),
            name=ServiceName(
                command.name,
            ),
            price=self._money(
                amount=command.amount,
                currency=command.currency,
            ),
            description=(ServiceDescription(command.description) if command.description else None),
            available_format_ids=_format_ids(command.participation_format_ids),
            billing_model=ServiceBillingModel(command.billing_model),
            required=command.required,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class EnableAdditionalServiceHandler(CompetitionCommandHandler):
    """Enable an additional service."""

    def handle(
        self,
        command: EnableAdditionalServiceCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.enable_additional_service(
            service_id=ServiceId.from_string(
                command.service_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class DisableAdditionalServiceHandler(CompetitionCommandHandler):
    """Disable an additional service."""

    def handle(
        self,
        command: DisableAdditionalServiceCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.disable_additional_service(
            service_id=ServiceId.from_string(
                command.service_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveAdditionalServiceHandler(CompetitionCommandHandler):
    """Remove an additional service."""

    def handle(
        self,
        command: RemoveAdditionalServiceCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_additional_service(
            service_id=ServiceId.from_string(
                command.service_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)
