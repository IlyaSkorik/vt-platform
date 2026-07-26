"""Unit tests for document kinds and their policies.

Pure domain — no database. These are the tests that make adding a third kind safe:
they assert the policy table is exhaustive and that the persistence mirror has not
drifted, so a new :class:`DocumentType` member cannot be half-added.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.diplomas.domain.issued_document import IssuedDocument
from apps.diplomas.domain.value_objects import DiplomaSnapshot, ParticipantSnapshot

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


def _snapshot() -> DiplomaSnapshot:
    return DiplomaSnapshot(participant=ParticipantSnapshot(display_name="Иванов Иван"))


class TestPolicyTable:
    def test_every_kind_declares_a_policy(self) -> None:
        # A new DocumentType member with no policy row must fail loudly here
        # rather than at render time.
        for document_type in DocumentType:
            assert policy_for(document_type).document_type is document_type

    def test_the_diploma_is_the_registry_document(self) -> None:
        policy = policy_for(DocumentType.DIPLOMA)

        assert policy.numbered
        assert policy.verifiable
        assert policy.awards_degree
        assert policy.is_registry_document
        # The organizer publishes a diploma deliberately, after the ceremony.
        assert not policy.publishes_on_generation

    def test_a_thank_you_is_a_courtesy_not_an_award(self) -> None:
        policy = policy_for(DocumentType.THANK_YOU)

        assert not policy.numbered
        assert not policy.verifiable
        assert not policy.awards_degree
        assert not policy.is_registry_document
        # Nothing to withhold, so it reaches the participant immediately.
        assert policy.publishes_on_generation

    def test_persistence_choices_mirror_the_domain_enum(self) -> None:
        from apps.diplomas.infrastructure.models import DocumentTypeChoices

        assert {t.value for t in DocumentType} == set(DocumentTypeChoices.values)

    def test_the_layout_serializer_accepts_every_diploma_field(self) -> None:
        from apps.diplomas.presentation.api.v1.diplomas.serializers import _FIELD_TYPES

        # The diploma set is the full catalogue; drift here would silently make a
        # field unplaceable or unvalidated.
        assert policy_for(DocumentType.DIPLOMA).field_types == frozenset(_FIELD_TYPES)


class TestThankYouFields:
    """What a courtesy letter may carry — and, mostly, what it may not."""

    def test_keeps_only_who_taught_whom_and_where(self) -> None:
        assert policy_for(DocumentType.THANK_YOU).field_types == frozenset(
            {
                "participant_name",
                "teacher",
                "competition_name",
                "competition_date",
                "competition_city",
                "free_text",
            }
        )

    @pytest.mark.parametrize(
        "field_type",
        ["award_degree", "qr_block", "diploma_issue_date", "nomination_block", "work", "organization", "participant_age"],
    )
    def test_refuses_what_belongs_to_a_diploma(self, field_type: str) -> None:
        thanks = policy_for(DocumentType.THANK_YOU)
        diploma = policy_for(DocumentType.DIPLOMA)

        assert not thanks.allows_field(field_type)
        # …each of which is legitimate on a diploma.
        assert diploma.allows_field(field_type)

    def test_thanks_a_person_rather_than_crediting_a_role(self) -> None:
        # A diploma credits a teacher in a stated capacity ("Педагог: ФИО");
        # a letter simply thanks them.
        assert policy_for(DocumentType.DIPLOMA).teacher_roles
        assert not policy_for(DocumentType.THANK_YOU).teacher_roles

    def test_is_addressed_to_one_teacher_at_a_time(self) -> None:
        # Two teachers on an entry mean two letters, each to its own recipient.
        assert policy_for(DocumentType.THANK_YOU).per_teacher
        # A diploma belongs to the performance and lists every teacher on one sheet.
        assert not policy_for(DocumentType.DIPLOMA).per_teacher


class TestIssuedDocument:
    def _document(self, document_type: DocumentType) -> IssuedDocument:
        return IssuedDocument.create(
            document_id=uuid.uuid4(),
            document_type=document_type,
            competition_id=uuid.uuid4(),
            submission_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            snapshot=_snapshot(),
            now=_NOW,
        )

    def test_starts_unrendered_and_unpublished(self) -> None:
        document = self._document(DocumentType.THANK_YOU)

        assert document.pdf_path is None
        assert document.published_at is None
        assert not document.is_published

    def test_publishes_on_render_when_the_policy_says_so(self) -> None:
        document = self._document(DocumentType.THANK_YOU).with_pdf("/media/x.pdf", now=_NOW)

        # This is "appears in the cabinet with no organizer action", enforced by
        # the policy rather than by the caller remembering to publish.
        assert document.is_published
        assert document.published_at == _NOW
        assert document.pdf_path == "/media/x.pdf"

    def test_recording_a_pdf_is_a_new_value(self) -> None:
        original = self._document(DocumentType.THANK_YOU)
        updated = original.with_pdf("/media/x.pdf", now=_NOW)

        assert original.pdf_path is None
        assert updated.version == original.version + 1

    def test_snapshot_is_frozen_at_creation(self) -> None:
        document = self._document(DocumentType.THANK_YOU)

        assert document.snapshot.participant.display_name == "Иванов Иван"
        with pytest.raises(AttributeError):
            document.snapshot.participant.display_name = "Кто-то другой"  # type: ignore[misc]
