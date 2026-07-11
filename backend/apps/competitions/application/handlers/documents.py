"""Use cases: competition documents."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddDocumentCommand,
    PublishDocumentCommand,
    RemoveDocumentCommand,
    UnpublishDocumentCommand,
    UpdateDocumentCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import (
    DocumentCategory,
    DocumentDescription,
    DocumentId,
    DocumentTitle,
    DocumentVisibility,
    FileReference,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddDocumentHandler",
    "PublishDocumentHandler",
    "RemoveDocumentHandler",
    "UnpublishDocumentHandler",
    "UpdateDocumentHandler",
)


class AddDocumentHandler(CompetitionCommandHandler):
    """Add a document."""

    def handle(
        self,
        command: AddDocumentCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.add_document(
            document_id=DocumentId.from_uuid(
                self._uuids.new(),
            ),
            title=DocumentTitle(command.title),
            category=DocumentCategory(command.category),
            visibility=DocumentVisibility(command.visibility),
            file=FileReference(command.file_reference),
            description=(DocumentDescription(command.description) if command.description else None),
            sort_order=command.sort_order,
            published=command.published,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class UpdateDocumentHandler(CompetitionCommandHandler):
    """Update a document."""

    def handle(
        self,
        command: UpdateDocumentCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.update_document(
            document_id=DocumentId.from_string(
                command.document_id,
            ),
            title=DocumentTitle(command.title),
            category=DocumentCategory(command.category),
            visibility=DocumentVisibility(command.visibility),
            file=FileReference(command.file_reference),
            description=(DocumentDescription(command.description) if command.description else None),
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class PublishDocumentHandler(CompetitionCommandHandler):
    """Publish a document."""

    def handle(
        self,
        command: PublishDocumentCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.publish_document(
            document_id=DocumentId.from_string(
                command.document_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class UnpublishDocumentHandler(CompetitionCommandHandler):
    """Unpublish a document."""

    def handle(
        self,
        command: UnpublishDocumentCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.unpublish_document(
            document_id=DocumentId.from_string(
                command.document_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveDocumentHandler(CompetitionCommandHandler):
    """Remove a document."""

    def handle(
        self,
        command: RemoveDocumentCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_document(
            document_id=DocumentId.from_string(
                command.document_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)
