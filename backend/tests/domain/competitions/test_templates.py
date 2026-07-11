"""Unit tests for the CompetitionTemplate aggregate and Competition.from_template."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from apps.competitions.domain.entities import Competition
from apps.competitions.domain.exceptions import (
    DirectConstructionError,
    DisciplineCategoryMismatchError,
    DuplicateCategoryError,
    OverlappingAgeRangeError,
)
from apps.competitions.domain.templates import CompetitionTemplate
from apps.competitions.domain.value_objects import (
    AdmissionCombination,
    AgeCategoryId,
    AgeCategoryName,
    AgeRange,
    CategoryId,
    CategoryName,
    CompetitionId,
    CompetitionTitle,
    DisciplineId,
    DisciplineName,
    FileReference,
    Money,
    OrganizerId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantGroupName,
    ParticipationFormat,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    Season,
    TemplateId,
    TemplateName,
)

NOW = datetime(2026, 7, 10, tzinfo=UTC)


@dataclass
class TemplateFixture:
    template: CompetitionTemplate
    offline: AdmissionCombination
    online: AdmissionCombination


def _template() -> TemplateFixture:
    t = CompetitionTemplate.create(template_id=TemplateId.generate(), name=TemplateName("Standard Vocal"), now=NOW)
    cat = t.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
    disc = t.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
    age = t.add_age_category(age_category_id=AgeCategoryId.generate(), category_id=cat.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW)
    grp = t.add_participant_group(
        participant_group_id=ParticipantGroupId.generate(),
        category_id=cat.id,
        name=ParticipantGroupName("Solo"),
        count_range=ParticipantCountRange(1, 1),
        now=NOW,
    )
    t.enable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW)
    t.enable_format(participation_format=ParticipationFormat.ONLINE, now=NOW)
    offline = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.OFFLINE)
    online = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.ONLINE)
    t.add_admission_rule(combination=offline, now=NOW)
    t.add_admission_rule(combination=online, now=NOW)
    t.add_pricing_rule(combination=offline, price_per_participant=Money.of("1500"), now=NOW)
    t.add_pricing_rule(combination=online, price_per_participant=Money.of("900"), now=NOW)
    return TemplateFixture(t, offline, online)


class TestTemplateInvariants:
    def test_direct_construction_refused(self) -> None:
        with pytest.raises(DirectConstructionError):
            CompetitionTemplate(_token=object(), _id=TemplateId.generate(), _name=TemplateName("x"), _created_at=NOW, _updated_at=NOW)

    def test_same_invariants_as_competition(self) -> None:
        t = CompetitionTemplate.create(template_id=TemplateId.generate(), name=TemplateName("t"), now=NOW)
        cat = t.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        with pytest.raises(DuplicateCategoryError):
            t.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        t.add_age_category(age_category_id=AgeCategoryId.generate(), category_id=cat.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW)
        with pytest.raises(OverlappingAgeRangeError):
            t.add_age_category(age_category_id=AgeCategoryId.generate(), category_id=cat.id, name=AgeCategoryName("7-9"), age_range=AgeRange(7, 9), now=NOW)

    def test_admission_reference_validated(self) -> None:
        t = CompetitionTemplate.create(template_id=TemplateId.generate(), name=TemplateName("t"), now=NOW)
        cat = t.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        other = t.add_category(category_id=CategoryId.generate(), name=CategoryName("Dance"), now=NOW)
        disc = t.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
        age = t.add_age_category(age_category_id=AgeCategoryId.generate(), category_id=cat.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW)
        grp = t.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            category_id=cat.id,
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        t.enable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW)
        bad = AdmissionCombination(other.id, disc.id, age.id, grp.id, ParticipationFormat.OFFLINE)
        with pytest.raises(DisciplineCategoryMismatchError):
            t.add_admission_rule(combination=bad, now=NOW)


class TestFromTemplate:
    def test_clones_config_with_fresh_ids(self) -> None:
        fx = _template()
        competition, events = Competition.from_template(
            competition_id=CompetitionId.generate(),
            title=CompetitionTitle("Spring Vocal"),
            season=Season("2027"),
            organizer_id=OrganizerId.from_uuid(CompetitionId.generate().value),
            template=fx.template,
            now=NOW,
        )
        assert competition.is_draft()
        assert [type(e).__name__ for e in events] == ["CompetitionCreated"]
        assert len(competition.categories) == 1
        assert len(competition.disciplines) == 1
        assert len(competition.admission_rules) == 2
        assert len(competition.pricing_rules) == 2
        assert competition.participation_formats == {ParticipationFormat.OFFLINE, ParticipationFormat.ONLINE}

        # Fresh ids: cloned category id differs from the template's.
        cloned_category = competition.categories[0]
        assert cloned_category.id != fx.template.categories[0].id

        # References preserved: the cloned discipline points at the cloned category.
        assert competition.disciplines[0].category_id == cloned_category.id

    def test_cloned_competition_is_admissible_and_priced(self) -> None:
        fx = _template()
        competition, _ = Competition.from_template(
            competition_id=CompetitionId.generate(),
            title=CompetitionTitle("Spring Vocal"),
            season=Season("2027"),
            organizer_id=OrganizerId.from_uuid(CompetitionId.generate().value),
            template=fx.template,
            now=NOW,
        )
        # Rebuild the combination from the cloned graph and check it works.
        cat = competition.categories[0]
        disc = competition.disciplines[0]
        age = competition.age_categories[0]
        grp = competition.participant_groups[0]
        combo = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.OFFLINE)
        assert competition.is_admissible(combo)
        assert competition.price_for(combo) == Money.of("1500")

        # Templates carry no regulation, so a clone is not yet publishable; adding
        # one satisfies the last requirement.
        assert not competition.publication_report().is_publishable
        competition.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("Rules"),
            version=RegulationVersion("1.0"),
            publication_date=date(2026, 7, 1),
            file=FileReference("s3://r.pdf"),
            now=NOW,
        )
        assert competition.publication_report().is_publishable

    def test_clones_are_independent(self) -> None:
        fx = _template()
        organizer = OrganizerId.from_uuid(CompetitionId.generate().value)
        a, _ = Competition.from_template(
            competition_id=CompetitionId.generate(),
            title=CompetitionTitle("A"),
            season=Season("2027"),
            organizer_id=organizer,
            template=fx.template,
            now=NOW,
        )
        b, _ = Competition.from_template(
            competition_id=CompetitionId.generate(),
            title=CompetitionTitle("B"),
            season=Season("2027"),
            organizer_id=organizer,
            template=fx.template,
            now=NOW,
        )
        assert a.categories[0].id != b.categories[0].id
