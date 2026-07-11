"""Use cases: competition information blocks."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddInformationBlockCommand,
    HideInformationBlockCommand,
    PublishInformationBlockCommand,
    RemoveInformationBlockCommand,
    UpdateInformationBlockCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import (
    InformationBlockId,
    InformationBlockTitle,
    RichText,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddInformationBlockHandler",
    "HideInformationBlockHandler",
    "PublishInformationBlockHandler",
    "RemoveInformationBlockHandler",
    "UpdateInformationBlockHandler",
)


class AddInformationBlockHandler(CompetitionCommandHandler):
    """Add an information block."""

    def handle(
        self,
        command: AddInformationBlockCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.add_information_block(
            block_id=InformationBlockId.from_uuid(
                self._uuids.new(),
            ),
            title=InformationBlockTitle(
                command.title,
            ),
            content=RichText(
                command.content,
            ),
            published=command.published,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class UpdateInformationBlockHandler(CompetitionCommandHandler):
    """Update an information block."""

    def handle(
        self,
        command: UpdateInformationBlockCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.update_information_block(
            block_id=InformationBlockId.from_string(
                command.block_id,
            ),
            title=InformationBlockTitle(
                command.title,
            ),
            content=RichText(
                command.content,
            ),
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class PublishInformationBlockHandler(CompetitionCommandHandler):
    """Publish an information block."""

    def handle(
        self,
        command: PublishInformationBlockCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.publish_information_block(
            block_id=InformationBlockId.from_string(
                command.block_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class HideInformationBlockHandler(CompetitionCommandHandler):
    """Hide an information block."""

    def handle(
        self,
        command: HideInformationBlockCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.hide_information_block(
            block_id=InformationBlockId.from_string(
                command.block_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class RemoveInformationBlockHandler(CompetitionCommandHandler):
    """Remove an information block."""

    def handle(
        self,
        command: RemoveInformationBlockCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_information_block(
            block_id=InformationBlockId.from_string(
                command.block_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)
