"""Use-case (handler) tests for the Competitions application layer.

Exercise the command/query handlers through the in-memory fakes — proving the
shared scaffolding works (``_require`` loads or raises, ``_persist`` saves and
publishes, ``_money`` builds prices), that DTOs are projected, and that the whole
create → configure → publish → open-registration flow runs end to end at the
use-case level (no HTTP, no database).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol, cast

import pytest

from apps.competitions.application.dto.commands import (
    AddAdmissionRuleCommand,
    AddAgeCategoryCommand,
    AddCategoryCommand,
    AddDisciplineCommand,
    AddParticipantGroupCommand,
    AddParticipationFormatCommand,
    AddPricingRuleCommand,
    AddRegulationCommand,
    CreateCompetitionCommand,
    MakeRegulationCurrentCommand,
    MarkConfiguredCommand,
    MarkReadyCommand,
    OpenRegistrationCommand,
    PublishCompetitionCommand,
    RenameCategoryCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.application.exceptions import CompetitionNotFoundError
from apps.competitions.application.handlers import (
    AddAdmissionRuleHandler,
    AddAgeCategoryHandler,
    AddCategoryHandler,
    AddDisciplineHandler,
    AddParticipantGroupHandler,
    AddParticipationFormatHandler,
    AddPricingRuleHandler,
    AddRegulationHandler,
    CreateCompetitionHandler,
    MakeRegulationCurrentHandler,
    MarkCompetitionConfiguredHandler,
    MarkCompetitionReadyHandler,
    OpenRegistrationHandler,
    PublishCompetitionHandler,
    RenameCategoryHandler,
)
from apps.competitions.application.handlers._support import CompetitionCommandHandler
from apps.competitions.domain.events import CompetitionCreated, CompetitionPublished

from .fakes import (
    FakeClock,
    FakeUuidGenerator,
    InMemoryCompetitionRepository,
    RecordingPublisher,
    new_uuid7,
)


class _Runner(Protocol):
    def handle(self, command: Any) -> CompetitionDetailView: ...


class _Deps:
    def __init__(self) -> None:
        self.repository = InMemoryCompetitionRepository()
        self.clock = FakeClock()
        self.publisher = RecordingPublisher()
        self.uuids = FakeUuidGenerator()

    def build(self, handler_cls: type[CompetitionCommandHandler]) -> _Runner:
        return cast(
            "_Runner",
            handler_cls(
                repository=self.repository,
                clock=self.clock,
                publisher=self.publisher,
                uuids=self.uuids,
            ),
        )


@pytest.fixture
def deps() -> _Deps:
    return _Deps()


def _create(deps: _Deps) -> CompetitionDetailView:
    return deps.build(CreateCompetitionHandler).handle(
        CreateCompetitionCommand(
            organizer_id=str(new_uuid7()),
            title="Autumn Cup",
            season="2025/2026",
        )
    )


def _configure_publishable(deps: _Deps, competition_id: str) -> CompetitionDetailView:
    """Drive every use case required for a publishable competition."""
    view = deps.build(AddCategoryHandler).handle(AddCategoryCommand(competition_id=competition_id, name="Vocal"))
    category_id = view.categories[0].id
    view = deps.build(AddDisciplineHandler).handle(AddDisciplineCommand(competition_id=competition_id, category_id=category_id, name="Solo Singing"))
    view = deps.build(AddParticipantGroupHandler).handle(
        AddParticipantGroupCommand(competition_id=competition_id, name="Solo", min_count=1, max_count=1)
    )
    group_id = view.participant_groups[0].id
    view = deps.build(AddAgeCategoryHandler).handle(
        AddAgeCategoryCommand(competition_id=competition_id, participant_group_id=group_id, name="7-10", min_age=7, max_age=10)
    )
    view = deps.build(AddParticipationFormatHandler).handle(AddParticipationFormatCommand(competition_id=competition_id, name="Очно"))
    combination = {
        "category_id": view.categories[0].id,
        "discipline_id": view.disciplines[0].id,
        "age_category_id": view.age_categories[0].id,
        "participant_group_id": view.participant_groups[0].id,
        "participation_format_id": view.participation_formats[0].id,
    }
    view = deps.build(AddAdmissionRuleHandler).handle(AddAdmissionRuleCommand(competition_id=competition_id, **combination))
    view = deps.build(AddPricingRuleHandler).handle(
        AddPricingRuleCommand(competition_id=competition_id, amount="50.00", currency="BYN", **combination)
    )
    view = deps.build(AddRegulationHandler).handle(
        AddRegulationCommand(
            competition_id=competition_id,
            title="Rules 2026",
            version="1.0",
            publication_date=date(2026, 1, 1),
            file_reference="s3://regs/2026.pdf",
        )
    )
    regulation_id = view.regulations[0].id
    return deps.build(MakeRegulationCurrentHandler).handle(MakeRegulationCurrentCommand(competition_id=competition_id, regulation_id=regulation_id))


def test_create_returns_draft_view_and_publishes_event(deps: _Deps) -> None:
    view = _create(deps)

    assert view.status == "DRAFT"
    assert view.title == "Autumn Cup"
    assert len(deps.repository.list_all()) == 1
    assert any(isinstance(e, CompetitionCreated) for e in deps.publisher.published)


def test_require_raises_when_competition_missing(deps: _Deps) -> None:
    with pytest.raises(CompetitionNotFoundError):
        deps.build(RenameCategoryHandler).handle(RenameCategoryCommand(competition_id=str(new_uuid7()), category_id=str(new_uuid7()), name="X"))


def test_add_category_is_reflected_in_view(deps: _Deps) -> None:
    view = _create(deps)
    updated = deps.build(AddCategoryHandler).handle(AddCategoryCommand(competition_id=view.id, name="Vocal"))
    assert [c.name for c in updated.categories] == ["Vocal"]


def test_full_workflow_reaches_registration_open(deps: _Deps) -> None:
    view = _create(deps)
    cid = view.id

    _configure_publishable(deps, cid)
    deps.build(MarkCompetitionConfiguredHandler).handle(MarkConfiguredCommand(competition_id=cid))
    deps.build(MarkCompetitionReadyHandler).handle(MarkReadyCommand(competition_id=cid))
    published = deps.build(PublishCompetitionHandler).handle(PublishCompetitionCommand(competition_id=cid))
    assert published.status == "PUBLISHED"
    assert any(isinstance(e, CompetitionPublished) for e in deps.publisher.published)

    opened = deps.build(OpenRegistrationHandler).handle(OpenRegistrationCommand(competition_id=cid))
    assert opened.status == "REGISTRATION_OPEN"


def test_publish_before_configuration_is_rejected(deps: _Deps) -> None:
    from apps.competitions.domain.exceptions import CompetitionStateError

    view = _create(deps)
    with pytest.raises(CompetitionStateError):
        deps.build(PublishCompetitionHandler).handle(PublishCompetitionCommand(competition_id=view.id))
