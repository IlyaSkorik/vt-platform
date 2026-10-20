"""Unit tests for the Competitions aggregate root and its child entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from apps.competitions.domain.entities import Competition
from apps.competitions.domain.events import (
    AdditionalServiceAdded,
    AdmissionRuleAdded,
    AdmissionRuleRemoved,
    CompetitionBrandingChanged,
    CompetitionCompleted,
    CompetitionContactAdded,
    CompetitionContactRemoved,
    CompetitionContactsConfigChanged,
    CompetitionCreated,
    CompetitionDeadlineChanged,
    CompetitionInformationHidden,
    CompetitionInformationPublished,
    CompetitionPublished,
    CompetitionSettingsChanged,
    CompetitionStarted,
    NominationRegistrationResumed,
    NominationRegistrationScheduled,
    NominationRegistrationStopped,
    NominationWaitlistDisabled,
    NominationWaitlistEnabled,
    ParticipationFormatDisabled,
    ParticipationFormatEnabled,
    PricingRuleAdded,
    PricingRuleRemoved,
    RegulationPublished,
    SubmissionEditingLocked,
    SubmissionEditingUnlocked,
)
from apps.competitions.domain.exceptions import (
    AdmissionRuleInUseError,
    AdmissionRuleNotFoundError,
    CategoryInUseError,
    CategoryNotFoundError,
    CompetitionAlreadyCompletedError,
    ConfigurationLockedError,
    ContactNotFoundError,
    DirectConstructionError,
    DisciplineCategoryMismatchError,
    DuplicateAdmissionRuleError,
    DuplicateCategoryError,
    DuplicateContactError,
    DuplicateDisciplineError,
    DuplicateInformationBlockError,
    DuplicateParticipantGroupError,
    DuplicatePricingRuleError,
    EmptyAdditionalServiceFormatsError,
    IllegalStatusTransitionError,
    InvalidRegistrationWindowError,
    OverlappingAgeRangeError,
    ParticipationFormatInUseError,
    ParticipationFormatNotEnabledError,
    PublicationRequirementsNotMetError,
    RegulationNotFoundError,
    ServiceNotFoundError,
)
from apps.competitions.domain.value_objects import (
    AdmissionCombination,
    AgeCategoryId,
    AgeCategoryName,
    AgeCategoryType,
    AgeRange,
    CategoryId,
    CategoryName,
    CompetitionId,
    CompetitionSettings,
    CompetitionStatus,
    CompetitionTitle,
    ContactId,
    ContactType,
    ContactValue,
    DisciplineId,
    DisciplineName,
    DocumentCategory,
    DocumentId,
    DocumentTitle,
    DocumentVisibility,
    FileReference,
    InformationBlockId,
    InformationBlockTitle,
    MixedAgeCalculationMethod,
    Money,
    OrganizerId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantGroupName,
    ParticipationFormatId,
    ParticipationFormatName,
    PublicationIssueCode,
    RegistrationDeadlines,
    RegistrationWindow,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    RichText,
    Season,
    ServiceBillingModel,
    ServiceId,
    ServiceName,
)

NOW = datetime(2026, 7, 10, tzinfo=UTC)


def _new_organizer() -> OrganizerId:
    return OrganizerId.from_uuid(CompetitionId.generate().value)


def _draft() -> Competition:
    competition, _ = Competition.draft(
        competition_id=CompetitionId.generate(),
        title=CompetitionTitle("Autumn Talents"),
        season=Season("2026/2027"),
        organizer_id=_new_organizer(),
        now=NOW,
    )
    return competition


@dataclass
class Fixture:
    competition: Competition
    category_id: CategoryId
    discipline_id: DisciplineId
    age_id: AgeCategoryId
    group_id: ParticipantGroupId
    offline: AdmissionCombination
    online: AdmissionCombination
    regulation_id: RegulationId


def _configured(*, priced: bool = True, with_regulation: bool = True) -> Fixture:
    """A competition with a single fully-wired combination, offline + online.

    When ``priced`` and ``with_regulation`` are both true the competition is
    publishable (has a current regulation, as publication now requires).
    """
    c = _draft()
    cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
    disc = c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
    grp = c.add_participant_group(
        participant_group_id=ParticipantGroupId.generate(),
        name=ParticipantGroupName("Solo"),
        count_range=ParticipantCountRange(1, 1),
        now=NOW,
    )
    age = c.add_age_category(
        age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
    )
    c.add_participation_format(format_id=ParticipationFormatId.generate(), name=ParticipationFormatName("Очно"), now=NOW)
    c.add_participation_format(format_id=ParticipationFormatId.generate(), name=ParticipationFormatName("Онлайн"), now=NOW)
    by_name = {f.name.value: f for f in c.participation_formats}
    offline_fmt = by_name["Очно"]
    online_fmt = by_name["Онлайн"]
    offline = AdmissionCombination(cat.id, disc.id, age.id, grp.id, offline_fmt.id)
    online = AdmissionCombination(cat.id, disc.id, age.id, grp.id, online_fmt.id)
    c.add_admission_rule(combination=offline, now=NOW)
    c.add_admission_rule(combination=online, now=NOW)
    if priced:
        c.add_pricing_rule(combination=offline, price_per_participant=Money.of("1500"), now=NOW)
        c.add_pricing_rule(combination=online, price_per_participant=Money.of("900"), now=NOW)
    regulation_id = RegulationId.generate()
    if with_regulation:
        c.add_regulation(
            regulation_id=regulation_id,
            title=RegulationTitle("Rules"),
            version=RegulationVersion("1.0"),
            publication_date=date(2026, 7, 1),
            file=FileReference("s3://rules.pdf"),
            now=NOW,
        )
    return Fixture(c, cat.id, disc.id, age.id, grp.id, offline, online, regulation_id)


def _completed() -> Competition:
    """A publishable competition driven all the way to the terminal COMPLETED state."""
    c = _configured().competition
    c.mark_configured(now=NOW)
    c.mark_ready(now=NOW)
    c.publish(now=NOW)
    c.start(now=NOW)
    c.complete(now=NOW)
    return c


def _published() -> tuple[Competition, CategoryId]:
    """A publishable competition driven to PUBLISHED; returns it and its nomination id."""
    fx = _configured()
    c = fx.competition
    c.mark_configured(now=NOW)
    c.mark_ready(now=NOW)
    c.publish(now=NOW)
    return c, fx.category_id


class TestDraftAndConstruction:
    def test_draft_starts_in_draft_and_emits_created(self) -> None:
        c, events = Competition.draft(
            competition_id=CompetitionId.generate(),
            title=CompetitionTitle("T"),
            season=Season("2026"),
            organizer_id=_new_organizer(),
            now=NOW,
        )
        assert c.is_draft()
        assert [type(e).__name__ for e in events] == ["CompetitionCreated"]
        assert isinstance(events[0], CompetitionCreated)

    def test_direct_construction_refused(self) -> None:
        with pytest.raises(DirectConstructionError):
            Competition(
                _token=object(),
                _id=CompetitionId.generate(),
                _title=CompetitionTitle("x"),
                _season=Season("s"),
                _organizer_id=_new_organizer(),
                _status=CompetitionStatus.DRAFT,
                _created_at=NOW,
                _updated_at=NOW,
            )


class TestTaxonomyInvariants:
    def test_duplicate_category_rejected(self) -> None:
        c = _draft()
        c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        with pytest.raises(DuplicateCategoryError):
            c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)

    def test_duplicate_discipline_within_category_rejected(self) -> None:
        c = _draft()
        cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
        with pytest.raises(DuplicateDisciplineError):
            c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)

    def test_overlapping_age_range_rejected(self) -> None:
        c = _draft()
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        with pytest.raises(OverlappingAgeRangeError):
            c.add_age_category(
                age_category_id=AgeCategoryId.generate(),
                participant_group_id=grp.id,
                name=AgeCategoryName("8-10"),
                age_range=AgeRange(8, 10),
                now=NOW,
            )

    def test_non_overlapping_age_range_allowed(self) -> None:
        c = _draft()
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("9-11"), age_range=AgeRange(9, 11), now=NOW
        )
        assert len(c.age_categories) == 2

    def test_mixed_age_category_may_overlap_standard_bands(self) -> None:
        # A mixed band spans the ages its standard neighbours cover — that is the point of it.
        c = _draft()
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(),
            participant_group_id=grp.id,
            name=AgeCategoryName("Смешанная 6-12"),
            age_range=AgeRange(6, 12),
            now=NOW,
            age_category_type=AgeCategoryType.MIXED,
            mixed_calculation_method=MixedAgeCalculationMethod.AVERAGE,
        )
        assert len(c.age_categories) == 2

    def test_standard_age_category_may_overlap_existing_mixed_band(self) -> None:
        c = _draft()
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(),
            participant_group_id=grp.id,
            name=AgeCategoryName("Смешанная 6-12"),
            age_range=AgeRange(6, 12),
            now=NOW,
            age_category_type=AgeCategoryType.MIXED,
            mixed_calculation_method=MixedAgeCalculationMethod.AVERAGE,
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        assert len(c.age_categories) == 2

    def test_turning_mixed_band_into_standard_revalidates_overlap(self) -> None:
        c = _draft()
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        mixed = c.add_age_category(
            age_category_id=AgeCategoryId.generate(),
            participant_group_id=grp.id,
            name=AgeCategoryName("Смешанная 6-12"),
            age_range=AgeRange(6, 12),
            now=NOW,
            age_category_type=AgeCategoryType.MIXED,
            mixed_calculation_method=MixedAgeCalculationMethod.AVERAGE,
        )
        with pytest.raises(OverlappingAgeRangeError):
            c.update_age_category(
                age_category_id=mixed.id,
                now=NOW,
                age_category_type=AgeCategoryType.STANDARD,
                mixed_calculation_method=None,
            )

    def test_age_range_may_repeat_across_participant_groups(self) -> None:
        # Age bands are scoped per group, so the same range is fine in a different group.
        c = _draft()
        solo = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        duet = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Duet"),
            count_range=ParticipantCountRange(2, 2),
            now=NOW,
        )
        rng = AgeRange(6, 8)
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=solo.id, name=AgeCategoryName("6-8"), age_range=rng, now=NOW
        )
        c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=duet.id, name=AgeCategoryName("6-8"), age_range=rng, now=NOW
        )
        assert len(c.age_categories) == 2

    def test_overlapping_participant_range_allowed_with_distinct_names(self) -> None:
        # Two groups may share the same headcount as long as their names differ:
        # the applicant picks the group explicitly, so ranges need not be disjoint.
        c = _draft()
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo (профи)"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        assert len(c.participant_groups) == 2

    def test_participant_groups_are_competition_wide(self) -> None:
        # Groups are no longer scoped per nomination; a duplicate name is refused globally.
        c = _draft()
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        with pytest.raises(DuplicateParticipantGroupError):
            c.add_participant_group(
                participant_group_id=ParticipantGroupId.generate(),
                name=ParticipantGroupName("Solo"),
                count_range=ParticipantCountRange(2, 4),
                now=NOW,
            )

    def test_update_participant_group_renames_and_resizes(self) -> None:
        from apps.competitions.domain.value_objects import ParticipantGroupDescription

        c = _draft()
        group = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.update_participant_group(
            participant_group_id=group.id,
            name=ParticipantGroupName("Duet"),
            count_range=ParticipantCountRange(2, 2),
            description=ParticipantGroupDescription("Two performers"),
            sort_order=3,
            now=NOW,
        )
        updated = c.participant_groups[0]
        assert updated.name.value == "Duet"
        assert updated.count_range.min_count == 2
        assert updated.description is not None
        assert updated.description.value == "Two performers"
        assert updated.sort_order == 3

    def test_update_participant_group_allows_overlapping_range(self) -> None:
        c = _draft()
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        duet = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Duet"),
            count_range=ParticipantCountRange(2, 2),
            now=NOW,
        )
        c.update_participant_group(
            participant_group_id=duet.id,
            count_range=ParticipantCountRange(1, 2),
            now=NOW,
        )
        updated = next(g for g in c.participant_groups if g.id == duet.id)
        assert updated.count_range == ParticipantCountRange(1, 2)


class TestAdmissionAndPricing:
    def test_admission_rule_added_event(self) -> None:
        fx = _configured(priced=False)
        c = _draft()
        cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        disc = c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        age = c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        c.add_participation_format(format_id=ParticipationFormatId.generate(), name=ParticipationFormatName("Очно"), now=NOW)
        fmt = c.participation_formats[0]
        combo = AdmissionCombination(cat.id, disc.id, age.id, grp.id, fmt.id)
        events = c.add_admission_rule(combination=combo, now=NOW)
        assert isinstance(events[0], AdmissionRuleAdded)
        assert c.is_admissible(combo)
        assert fx.competition.is_admissible(fx.offline)

    def test_discipline_category_mismatch_rejected(self) -> None:
        fx = _configured()
        other_cat = fx.competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Dance"), now=NOW)
        bad = AdmissionCombination(other_cat.id, fx.discipline_id, fx.age_id, fx.group_id, fx.offline.participation_format_id)
        with pytest.raises(DisciplineCategoryMismatchError):
            fx.competition.add_admission_rule(combination=bad, now=NOW)

    def test_format_not_enabled_rejected(self) -> None:
        c = _draft()
        cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        disc = c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        age = c.add_age_category(
            age_category_id=AgeCategoryId.generate(), participant_group_id=grp.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=NOW
        )
        c.add_participation_format(
            format_id=ParticipationFormatId.generate(),
            name=ParticipationFormatName("Очно"),
            now=NOW,
            enabled=False,
        )
        fmt = c.participation_formats[0]
        combo = AdmissionCombination(cat.id, disc.id, age.id, grp.id, fmt.id)
        with pytest.raises(ParticipationFormatNotEnabledError):
            c.add_admission_rule(combination=combo, now=NOW)

    def test_duplicate_admission_rejected(self) -> None:
        fx = _configured()
        with pytest.raises(DuplicateAdmissionRuleError):
            fx.competition.add_admission_rule(combination=fx.offline, now=NOW)

    def test_pricing_requires_admission_rule(self) -> None:
        fx = _configured(priced=False)
        # remove admission first to make it non-admissible
        fx.competition.remove_admission_rule(combination=fx.offline, now=NOW)
        with pytest.raises(AdmissionRuleNotFoundError):
            fx.competition.add_pricing_rule(combination=fx.offline, price_per_participant=Money.of("100"), now=NOW)

    def test_duplicate_pricing_rejected(self) -> None:
        fx = _configured()
        with pytest.raises(DuplicatePricingRuleError):
            fx.competition.add_pricing_rule(combination=fx.offline, price_per_participant=Money.of("1"), now=NOW)

    def test_pricing_events_and_price_for(self) -> None:
        fx = _configured(priced=False)
        added = fx.competition.add_pricing_rule(combination=fx.offline, price_per_participant=Money.of("1500"), now=NOW)
        assert isinstance(added[0], PricingRuleAdded)
        assert fx.competition.price_for(fx.offline) == Money.of("1500")
        changed = fx.competition.change_price(combination=fx.offline, price_per_participant=Money.of("1200"), now=NOW)
        assert isinstance(changed[0], PricingRuleAdded)
        assert fx.competition.price_for(fx.offline) == Money.of("1200")
        removed = fx.competition.remove_pricing_rule(combination=fx.offline, now=NOW)
        assert isinstance(removed[0], PricingRuleRemoved)
        assert fx.competition.price_for(fx.offline) is None

    def test_offline_and_online_prices_differ(self) -> None:
        fx = _configured()
        assert fx.competition.price_for(fx.offline) == Money.of("1500")
        assert fx.competition.price_for(fx.online) == Money.of("900")

    def test_remove_admission_blocked_while_priced(self) -> None:
        fx = _configured()
        with pytest.raises(AdmissionRuleInUseError):
            fx.competition.remove_admission_rule(combination=fx.offline, now=NOW)
        events = fx.competition.remove_pricing_rule(combination=fx.offline, now=NOW)
        assert isinstance(events[0], PricingRuleRemoved)
        rm = fx.competition.remove_admission_rule(combination=fx.offline, now=NOW)
        assert isinstance(rm[0], AdmissionRuleRemoved)


class TestFormats:
    def test_add_and_soft_disable_events(self) -> None:
        c = _draft()
        format_id = ParticipationFormatId.generate()
        enabled = c.add_participation_format(format_id=format_id, name=ParticipationFormatName("Очно"), now=NOW)
        assert isinstance(enabled[0], ParticipationFormatEnabled)
        disabled = c.update_participation_format(format_id=format_id, enabled=False, now=NOW)
        assert isinstance(disabled[0], ParticipationFormatDisabled)
        reenabled = c.update_participation_format(format_id=format_id, enabled=True, now=NOW)
        assert isinstance(reenabled[0], ParticipationFormatEnabled)


class TestDeletionGuards:
    def test_remove_category_in_use_rejected(self) -> None:
        fx = _configured()
        with pytest.raises(CategoryInUseError):
            fx.competition.remove_category(category_id=fx.category_id, now=NOW)


class TestPublicationReport:
    def test_empty_draft_has_all_errors(self) -> None:
        report = _draft().publication_report()
        codes = {i.code for i in report.errors}
        assert PublicationIssueCode.NO_CATEGORIES in codes
        assert PublicationIssueCode.NO_ADMISSION_RULES in codes
        assert not report.is_publishable

    def test_missing_price_is_warning_not_blocking(self) -> None:
        # A festival may charge for nothing at all, so an unpriced combination is
        # reported for the organizer to notice — it does not hold back publication.
        fx = _configured(priced=False)
        report = fx.competition.publication_report()
        assert PublicationIssueCode.MISSING_PRICING_RULES in {i.code for i in report.warnings}
        assert PublicationIssueCode.MISSING_PRICING_RULES not in {i.code for i in report.errors}
        assert report.is_publishable

    def test_missing_regulation_is_blocking_error(self) -> None:
        fx = _configured(with_regulation=False)
        report = fx.competition.publication_report()
        assert not report.is_publishable
        assert PublicationIssueCode.MISSING_REGULATION in {i.code for i in report.errors}

    def test_regulation_makes_it_publishable(self) -> None:
        fx = _configured()  # includes a regulation
        assert fx.competition.publication_report().is_publishable

    def test_unused_format_is_warning(self) -> None:
        fx = _configured()
        # ONLINE is used; enable HYBRID-like extra? only OFFLINE/ONLINE exist and both used.
        # Remove online rules so ONLINE becomes unused.
        fx.competition.remove_pricing_rule(combination=fx.online, now=NOW)
        fx.competition.remove_admission_rule(combination=fx.online, now=NOW)
        report = fx.competition.publication_report()
        assert PublicationIssueCode.UNUSED_PARTICIPATION_FORMAT in {i.code for i in report.warnings}
        assert report.is_publishable


class TestLifecycle:
    def test_full_happy_path(self) -> None:
        fx = _configured()
        c = fx.competition
        assert c.mark_configured(now=NOW) == []
        assert str(c.status) == "CONFIGURED"
        assert c.mark_ready(now=NOW) == []
        assert str(c.status) == "READY"
        assert isinstance(c.publish(now=NOW)[0], CompetitionPublished)
        assert str(c.status) == "PUBLISHED"
        assert isinstance(c.start(now=NOW)[0], CompetitionStarted)
        assert str(c.status) == "RUNNING"
        assert isinstance(c.complete(now=NOW)[0], CompetitionCompleted)
        assert str(c.status) == "COMPLETED"

    def test_illegal_transition_publish_from_draft(self) -> None:
        fx = _configured()
        with pytest.raises(IllegalStatusTransitionError):
            fx.competition.publish(now=NOW)  # still DRAFT, not READY

    def test_illegal_transition_start_from_draft(self) -> None:
        with pytest.raises(IllegalStatusTransitionError):
            _draft().start(now=NOW)

    def test_mark_ready_refused_when_incomplete(self) -> None:
        c = _draft()
        c.mark_configured(now=NOW)
        with pytest.raises(PublicationRequirementsNotMetError):
            c.mark_ready(now=NOW)

    def test_free_festival_reaches_ready(self) -> None:
        # Nothing priced, everything else configured: a free festival is publishable.
        fx = _configured(priced=False)
        fx.competition.mark_configured(now=NOW)
        fx.competition.mark_ready(now=NOW)  # no raise
        assert isinstance(fx.competition.publish(now=NOW)[0], CompetitionPublished)

    def test_config_locked_after_ready(self) -> None:
        fx = _configured()
        fx.competition.mark_configured(now=NOW)
        fx.competition.mark_ready(now=NOW)
        with pytest.raises(ConfigurationLockedError):
            fx.competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Theatre"), now=NOW)

    def test_config_allowed_in_configured(self) -> None:
        fx = _configured()
        fx.competition.mark_configured(now=NOW)
        fx.competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Theatre"), now=NOW)  # no raise

    def test_revert_to_configured_then_edit(self) -> None:
        fx = _configured()
        fx.competition.mark_configured(now=NOW)
        fx.competition.mark_ready(now=NOW)
        fx.competition.revert_to_configured(now=NOW)
        assert fx.competition.status == CompetitionStatus.CONFIGURED
        fx.competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Theatre"), now=NOW)

    def test_completed_is_terminal_and_immutable(self) -> None:
        c = _completed()
        assert c.is_completed()
        with pytest.raises(IllegalStatusTransitionError):
            c.complete(now=NOW)  # COMPLETED is terminal
        with pytest.raises(CompetitionAlreadyCompletedError):
            c.add_document(
                document_id=DocumentId.generate(),
                title=DocumentTitle("M"),
                category=DocumentCategory.MEMO,
                visibility=DocumentVisibility.PUBLIC,
                file=FileReference("x"),
                now=NOW,
            )


class TestRegulations:
    def test_add_regulation_becomes_current_and_emits_event(self) -> None:
        c = _draft()
        _, events = c.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("Rules v1"),
            version=RegulationVersion("1.0"),
            publication_date=date(2026, 7, 1),
            file=FileReference("s3://r1.pdf"),
            now=NOW,
        )
        assert isinstance(events[0], RegulationPublished)
        assert c.current_regulation is not None
        assert c.current_regulation.version == RegulationVersion("1.0")

    def test_newest_regulation_is_current_but_previous_kept(self) -> None:
        c = _draft()
        r1, _ = c.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("v1"),
            version=RegulationVersion("1.0"),
            publication_date=date(2026, 7, 1),
            file=FileReference("a"),
            now=NOW,
        )
        r2, _ = c.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("v2"),
            version=RegulationVersion("2.0"),
            publication_date=date(2026, 7, 2),
            file=FileReference("b"),
            now=NOW,
        )
        assert c.current_regulation == r2
        assert len(c.regulations) == 2
        # switch current back to v1
        c.make_regulation_current(regulation_id=r1.id, now=NOW)
        assert c.current_regulation == r1

    def test_remove_current_promotes_latest_remaining(self) -> None:
        c = _draft()
        r1, _ = c.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("v1"),
            version=RegulationVersion("1.0"),
            publication_date=date(2026, 7, 1),
            file=FileReference("a"),
            now=NOW,
        )
        r2, _ = c.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("v2"),
            version=RegulationVersion("2.0"),
            publication_date=date(2026, 7, 2),
            file=FileReference("b"),
            now=NOW,
        )
        c.remove_regulation(regulation_id=r2.id, now=NOW)  # current was r2
        assert c.current_regulation == r1

    def test_remove_last_clears_current(self) -> None:
        c = _draft()
        r1, _ = c.add_regulation(
            regulation_id=RegulationId.generate(),
            title=RegulationTitle("v1"),
            version=RegulationVersion("1.0"),
            publication_date=date(2026, 7, 1),
            file=FileReference("a"),
            now=NOW,
        )
        c.remove_regulation(regulation_id=r1.id, now=NOW)
        assert c.current_regulation is None

    def test_make_missing_regulation_current_raises(self) -> None:
        c = _draft()
        with pytest.raises(RegulationNotFoundError):
            c.make_regulation_current(regulation_id=RegulationId.generate(), now=NOW)


class TestAdditionalServices:
    def test_add_service_scoped_to_formats_and_event(self) -> None:
        fx = _configured(priced=False)
        sid = ServiceId.generate()
        events = fx.competition.add_additional_service(
            service_id=sid,
            name=ServiceName("Medal"),
            price=Money.of("500"),
            available_format_ids=[fx.offline.participation_format_id],
            billing_model=ServiceBillingModel.PER_PERFORMANCE,
            now=NOW,
        )
        assert isinstance(events[0], AdditionalServiceAdded)
        (service,) = fx.competition.additional_services
        assert service.price == Money.of("500")
        assert service.billing_model is ServiceBillingModel.PER_PERFORMANCE
        assert service.is_available_for(fx.offline.participation_format_id)
        assert not service.is_available_for(fx.online.participation_format_id)
        assert service.total_for(3) == Money.of("500")
        assert service.is_enabled

    def test_per_participant_billing_multiplies_headcount(self) -> None:
        fx = _configured(priced=False)
        sid = ServiceId.generate()
        fx.competition.add_additional_service(
            service_id=sid,
            name=ServiceName("Shipping"),
            price=Money.of("10"),
            available_format_ids=[fx.online.participation_format_id],
            billing_model=ServiceBillingModel.PER_PARTICIPANT,
            now=NOW,
        )
        assert fx.competition.additional_services[0].total_for(4) == Money.of("40")

    def test_requires_at_least_one_format(self) -> None:
        c = _draft()
        with pytest.raises(EmptyAdditionalServiceFormatsError):
            c.add_additional_service(
                service_id=ServiceId.generate(),
                name=ServiceName("Medal"),
                price=Money.of("100"),
                available_format_ids=[],
                now=NOW,
            )

    def test_enable_disable_update_remove(self) -> None:
        fx = _configured(priced=False)
        sid = ServiceId.generate()
        fx.competition.add_additional_service(
            service_id=sid,
            name=ServiceName("Video"),
            price=Money.of("1000"),
            available_format_ids=[fx.offline.participation_format_id],
            now=NOW,
        )
        fx.competition.disable_additional_service(service_id=sid, now=NOW)
        assert not fx.competition.additional_services[0].is_enabled
        fx.competition.enable_additional_service(service_id=sid, now=NOW)
        assert fx.competition.additional_services[0].is_enabled
        fx.competition.update_additional_service(
            service_id=sid,
            name=ServiceName("Pro Video"),
            price=Money.of("1200"),
            description=None,
            available_format_ids=[fx.offline.participation_format_id, fx.online.participation_format_id],
            billing_model=ServiceBillingModel.PER_PARTICIPANT,
            required=True,
            sort_order=2,
            now=NOW,
        )
        updated = fx.competition.additional_services[0]
        assert updated.name == ServiceName("Pro Video")
        assert updated.required is True
        assert updated.sort_order == 2
        assert updated.is_available_for(fx.online.participation_format_id)
        fx.competition.remove_additional_service(service_id=sid, now=NOW)
        assert fx.competition.additional_services == ()

    def test_format_in_use_by_service_blocks_removal(self) -> None:
        fx = _configured(priced=False)
        # Drop admission/pricing references to formats first so only the service holds them.
        for combination in (fx.offline, fx.online):
            fx.competition.remove_admission_rule(combination=combination, now=NOW)
        unused = ParticipationFormatId.generate()
        fx.competition.add_participation_format(format_id=unused, name=ParticipationFormatName("Correspondence"), now=NOW)
        fx.competition.add_additional_service(
            service_id=ServiceId.generate(),
            name=ServiceName("E-diploma"),
            price=Money.of("50"),
            available_format_ids=[unused],
            now=NOW,
        )
        with pytest.raises(ParticipationFormatInUseError):
            fx.competition.remove_participation_format(format_id=unused, now=NOW)

    def test_missing_service_raises(self) -> None:
        c = _draft()
        with pytest.raises(ServiceNotFoundError):
            c.disable_additional_service(service_id=ServiceId.generate(), now=NOW)


class TestEventSerialization:
    def test_admission_and_pricing_events_serialize(self) -> None:
        fx = _configured(priced=False)
        (added,) = fx.competition.add_pricing_rule(combination=fx.offline, price_per_participant=Money.of("1500"), now=NOW)
        payload = added.to_dict()
        assert payload["event_type"] == "PricingRuleAdded"
        assert payload["amount"] == "1500.00"
        assert payload["currency"] == "BYN"
        assert isinstance(payload["category_id"], str)


class TestSettings:
    def test_default_settings_present(self) -> None:
        assert _draft().settings == CompetitionSettings.default()

    def test_update_settings_emits_event(self) -> None:
        c = _draft()
        new = CompetitionSettings.default().with_changes(require_parent_guardian=True, allow_multiple_applications=True)
        events = c.update_settings(settings=new, now=NOW)
        assert isinstance(events[0], CompetitionSettingsChanged)
        assert c.settings.require_parent_guardian is True
        assert c.settings.allow_multiple_applications is True

    def test_settings_locked_after_complete(self) -> None:
        c = _completed()
        with pytest.raises(CompetitionAlreadyCompletedError):
            c.update_settings(settings=CompetitionSettings.default(), now=NOW)


class TestContactsConfig:
    def test_default_contacts_config_present(self) -> None:
        from apps.competitions.domain.contacts_configuration import ContactsConfiguration

        assert _draft().contacts_config == ContactsConfiguration.default()

    def test_update_contacts_config_emits_event(self) -> None:
        from apps.competitions.domain.contacts_configuration import (
            ContactProfileOverride,
            ContactsConfiguration,
            TeamContact,
        )

        c = _draft()
        new = ContactsConfiguration(
            use_organization_contacts=False,
            override=ContactProfileOverride(phone="+375 29 111-11-11"),
            team_contacts=(
                TeamContact(
                    id="01900000-0000-7000-8000-000000000099",
                    name="Ivan",
                    position="Manager",
                ),
            ),
        )
        events = c.update_contacts_config(config=new, now=NOW)
        assert isinstance(events[0], CompetitionContactsConfigChanged)
        assert c.contacts_config.use_organization_contacts is False
        assert c.contacts_config.override.phone == "+375 29 111-11-11"
        assert c.contacts_config.team_contacts[0].name == "Ivan"

    def test_contacts_config_locked_after_complete(self) -> None:
        from apps.competitions.domain.contacts_configuration import ContactsConfiguration

        c = _completed()
        with pytest.raises(CompetitionAlreadyCompletedError):
            c.update_contacts_config(config=ContactsConfiguration.default(), now=NOW)


class TestLandingConfig:
    def test_default_landing_config_present(self) -> None:
        from apps.competitions.domain.landing_configuration import LandingConfiguration

        assert _draft().landing_config == LandingConfiguration.default()

    def test_update_landing_config_emits_event(self) -> None:
        from apps.competitions.domain.events import CompetitionLandingConfigurationChanged
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_FAQ_ID,
            SYSTEM_BLOCK_GALLERY_ID,
            SYSTEM_BLOCK_HERO_ID,
            SYSTEM_BLOCK_JURY_ID,
            SYSTEM_BLOCK_PARTNERS_ID,
            SYSTEM_BLOCK_VENUE_ID,
            LandingBlock,
            LandingBlockType,
            LandingConfiguration,
        )

        c = _draft()
        new = LandingConfiguration(
            blocks=(
                LandingBlock(
                    id=SYSTEM_BLOCK_HERO_ID,
                    type=LandingBlockType.HERO,
                    enabled=True,
                    sort_order=0,
                    title="Spring Festival",
                    subtitle="Join us",
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_VENUE_ID,
                    type=LandingBlockType.VENUE,
                    enabled=True,
                    sort_order=1,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_JURY_ID,
                    type=LandingBlockType.JURY,
                    enabled=False,
                    sort_order=2,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_PARTNERS_ID,
                    type=LandingBlockType.PARTNERS,
                    enabled=False,
                    sort_order=3,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_GALLERY_ID,
                    type=LandingBlockType.GALLERY,
                    enabled=False,
                    sort_order=4,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_FAQ_ID,
                    type=LandingBlockType.FAQ,
                    enabled=False,
                    sort_order=5,
                ),
            )
        )
        events = c.update_landing_config(config=new, now=NOW)
        assert isinstance(events[0], CompetitionLandingConfigurationChanged)
        assert c.landing_config.blocks[0].title == "Spring Festival"

    def test_landing_config_locked_after_complete(self) -> None:
        from apps.competitions.domain.landing_configuration import LandingConfiguration

        c = _completed()
        with pytest.raises(CompetitionAlreadyCompletedError):
            c.update_landing_config(config=LandingConfiguration.default(), now=NOW)


class TestDeadlines:
    def test_update_deadlines_and_queries(self) -> None:
        c = _draft()
        deadline = datetime(2026, 8, 1, tzinfo=UTC)
        events = c.update_deadlines(deadlines=RegistrationDeadlines(application=deadline, music_upload=deadline), now=NOW)
        assert isinstance(events[0], CompetitionDeadlineChanged)
        # Application acceptance is scheduled per nomination (see TestNominationRegistration),
        # not by a competition-wide application deadline; only the other deadlines gate here.
        assert c.is_music_upload_allowed(datetime(2026, 7, 15, tzinfo=UTC))
        # No payment deadline set -> always allowed (until archived).
        assert c.is_payment_allowed(datetime(2030, 1, 1, tzinfo=UTC))

    def test_all_disallowed_when_completed(self) -> None:
        c = _completed()
        assert not c.is_application_allowed(NOW)
        assert not c.is_payment_allowed(NOW)
        assert not c.is_music_upload_allowed(NOW)


class TestNominationRegistration:
    def test_unconfigured_nomination_is_closed(self) -> None:
        c, cat_id = _published()
        # A nomination with no schedule accepts nothing and does not open the competition.
        assert not c.accepts_submissions_for(cat_id, NOW)
        assert not c.is_any_nomination_open(NOW)
        assert not c.is_application_allowed(NOW)

    def test_schedule_window_opens_within_bounds(self) -> None:
        c, cat_id = _published()
        opens = datetime(2026, 8, 1, tzinfo=UTC)
        closes = datetime(2026, 8, 31, tzinfo=UTC)
        events = c.schedule_nomination_registration(category_id=cat_id, opens_at=opens, closes_at=closes, now=NOW)
        assert isinstance(events[0], NominationRegistrationScheduled)
        assert not c.accepts_submissions_for(cat_id, datetime(2026, 7, 20, tzinfo=UTC))  # before open
        assert c.accepts_submissions_for(cat_id, datetime(2026, 8, 15, tzinfo=UTC))  # within
        assert not c.accepts_submissions_for(cat_id, datetime(2026, 9, 1, tzinfo=UTC))  # after close
        assert c.is_any_nomination_open(datetime(2026, 8, 15, tzinfo=UTC))

    def test_open_ended_bounds(self) -> None:
        c, cat_id = _published()
        # Only a close instant -> open until then.
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 8, 31, tzinfo=UTC), now=NOW)
        assert c.accepts_submissions_for(cat_id, datetime(2026, 7, 1, tzinfo=UTC))
        assert not c.accepts_submissions_for(cat_id, datetime(2026, 9, 1, tzinfo=UTC))

    def test_stop_and_resume(self) -> None:
        c, cat_id = _published()
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 12, 31, tzinfo=UTC), now=NOW)
        at = datetime(2026, 8, 15, tzinfo=UTC)
        assert c.accepts_submissions_for(cat_id, at)
        stopped = c.stop_nomination_registration(category_id=cat_id, now=NOW)
        assert isinstance(stopped[0], NominationRegistrationStopped)
        assert not c.accepts_submissions_for(cat_id, at)  # early-stopped despite an open window
        resumed = c.resume_nomination_registration(category_id=cat_id, now=NOW)
        assert isinstance(resumed[0], NominationRegistrationResumed)
        assert c.accepts_submissions_for(cat_id, at)

    def test_submissions_gated_by_status(self) -> None:
        # A wide-open window admits applications only while PUBLISHED or RUNNING —
        # never in DRAFT/CONFIGURED/READY, and never once COMPLETED.
        fx = _configured()
        c = fx.competition
        at = datetime(2026, 8, 15, tzinfo=UTC)
        c.schedule_nomination_registration(category_id=fx.category_id, closes_at=datetime(2027, 1, 1, tzinfo=UTC), now=NOW)
        assert not c.accepts_submissions_for(fx.category_id, at)  # DRAFT
        c.mark_configured(now=NOW)
        c.mark_ready(now=NOW)
        c.publish(now=NOW)
        assert c.accepts_submissions_for(fx.category_id, at)  # PUBLISHED
        c.start(now=NOW)
        assert c.accepts_submissions_for(fx.category_id, at)  # RUNNING
        c.complete(now=NOW)
        assert not c.accepts_submissions_for(fx.category_id, at)  # COMPLETED

    def test_invalid_window_rejected(self) -> None:
        with pytest.raises(InvalidRegistrationWindowError):
            RegistrationWindow(opens_at=datetime(2026, 9, 1, tzinfo=UTC), closes_at=datetime(2026, 8, 1, tzinfo=UTC))

    def test_schedule_unknown_nomination_rejected(self) -> None:
        c = _draft()
        with pytest.raises(CategoryNotFoundError):
            c.stop_nomination_registration(category_id=CategoryId.generate(), now=NOW)

    def test_registration_control_refused_after_complete(self) -> None:
        c = _completed()
        with pytest.raises(CompetitionAlreadyCompletedError):
            c.schedule_nomination_registration(category_id=CategoryId.generate(), closes_at=datetime(2026, 8, 1, tzinfo=UTC), now=NOW)


class TestSubmissionEditingLock:
    """Одна кнопка организатора, которая закрывает всё, что может менять заявитель.

    Отдельная от закрытия приёма, потому что отвечает на другой вопрос. Приём — про
    то, кого ещё пускают внутрь; у тех, кто внутри, файлы живут дольше, и это не
    побочный эффект, а то, ради чего сроки загрузки стоят позже срока заявок. Замок
    кончает и это: список финальный, программа собирается, двигаться больше нечему.
    """

    @staticmethod
    def _open_festival() -> tuple[Competition, CategoryId]:
        c, cat_id = _published()
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 12, 31, tzinfo=UTC), now=NOW)
        return c, cat_id

    def test_a_festival_starts_unlocked(self) -> None:
        c, _ = self._open_festival()

        assert not c.is_editing_locked
        assert c.editing_locked_at is None

    def test_locking_closes_registration_and_every_upload_window(self) -> None:
        c, cat_id = self._open_festival()
        at = datetime(2026, 8, 15, tzinfo=UTC)
        assert c.accepts_submissions_for(cat_id, at)
        assert c.is_music_upload_allowed(at)

        events = c.lock_submission_editing(now=NOW)

        assert isinstance(events[0], SubmissionEditingLocked)
        assert c.is_editing_locked
        assert not c.accepts_submissions_for(cat_id, at)
        assert not c.is_any_nomination_open(at)
        assert not c.is_music_upload_allowed(at)
        assert not c.is_media_upload_allowed(at)
        assert not c.is_document_upload_allowed(at)
        assert not c.is_correction_allowed(at)

    def test_the_waitlist_closes_with_it(self) -> None:
        # Очередь — дверь для опоздавших; замерший фестиваль никого не ждёт.
        c, cat_id = self._open_festival()
        c.enable_nomination_waitlist(category_id=cat_id, now=NOW)
        after = datetime(2027, 1, 15, tzinfo=UTC)
        assert c.accepts_waitlist_for(cat_id, after)

        c.lock_submission_editing(now=NOW)

        assert not c.accepts_waitlist_for(cat_id, after)
        assert not c.is_any_nomination_waitlisting(after)

    def test_payment_is_not_frozen(self) -> None:
        # Долг остаётся долгом: заявитель, которому закрыли оплату, — это заявитель,
        # которого организатор потом ловит вручную.
        c, _ = self._open_festival()

        c.lock_submission_editing(now=NOW)

        assert c.is_payment_allowed(datetime(2026, 8, 15, tzinfo=UTC))

    def test_locking_twice_keeps_the_first_instant(self) -> None:
        # Заявителю отвечают, когда правки закрылись, а не когда организатор в
        # последний раз нажал кнопку.
        c, _ = self._open_festival()
        later = datetime(2026, 9, 1, tzinfo=UTC)

        c.lock_submission_editing(now=NOW)
        again = c.lock_submission_editing(now=later)

        assert again == []
        assert c.editing_locked_at == NOW

    def test_unlocking_gives_the_calendar_back(self) -> None:
        c, cat_id = self._open_festival()
        at = datetime(2026, 8, 15, tzinfo=UTC)
        c.lock_submission_editing(now=NOW)

        events = c.unlock_submission_editing(now=NOW)

        assert isinstance(events[0], SubmissionEditingUnlocked)
        assert not c.is_editing_locked
        assert c.accepts_submissions_for(cat_id, at)
        assert c.is_music_upload_allowed(at)

    def test_unlocking_an_open_festival_changes_nothing(self) -> None:
        c, _ = self._open_festival()

        assert c.unlock_submission_editing(now=NOW) == []

    def test_a_completed_festival_has_nothing_left_to_lock(self) -> None:
        c = _completed()

        with pytest.raises(CompetitionAlreadyCompletedError):
            c.lock_submission_editing(now=NOW)


class TestMaterialUploadWindow:
    """Фонограмма, видео и фотографии закрываются своим сроком, а не сроком заявок.

    Раньше видео и фото падали на срок приёма: номер, попавший в фестиваль в
    последний день, уже не мог заменить присланное видео — ровно обратное тому, зачем
    сроки загрузки вообще стоят отдельно и позже.
    """

    def test_material_outlives_the_close_of_registration(self) -> None:
        c, cat_id = _published()
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 8, 31, tzinfo=UTC), now=NOW)
        after_the_close = datetime(2026, 9, 15, tzinfo=UTC)
        assert not c.accepts_submissions_for(cat_id, after_the_close)

        assert c.is_music_upload_allowed(after_the_close)
        assert c.is_media_upload_allowed(after_the_close)
        assert c.is_document_upload_allowed(after_the_close)

    def test_video_and_photographs_follow_the_track_s_own_deadline(self) -> None:
        c, _ = _published()
        c.update_deadlines(deadlines=RegistrationDeadlines(music_upload=datetime(2026, 9, 1, tzinfo=UTC)), now=NOW)

        assert c.is_media_upload_allowed(datetime(2026, 8, 20, tzinfo=UTC))
        assert not c.is_media_upload_allowed(datetime(2026, 9, 2, tzinfo=UTC))


class TestNominationWaitlist:
    def test_waitlist_off_by_default(self) -> None:
        c, cat_id = _published()
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 8, 31, tzinfo=UTC), now=NOW)
        assert not c.accepts_waitlist_for(cat_id, datetime(2026, 9, 1, tzinfo=UTC))
        assert not c.is_any_nomination_waitlisting(datetime(2026, 9, 1, tzinfo=UTC))

    def test_waitlist_opens_only_behind_a_closed_door(self) -> None:
        # While the nomination is open there is nothing to wait for: offering both
        # doors at once would let an applicant pick the unpaid one.
        c, cat_id = _published()
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 8, 31, tzinfo=UTC), now=NOW)
        enabled = c.enable_nomination_waitlist(category_id=cat_id, now=NOW)
        assert isinstance(enabled[0], NominationWaitlistEnabled)
        open_at = datetime(2026, 8, 15, tzinfo=UTC)
        assert c.accepts_submissions_for(cat_id, open_at)
        assert not c.accepts_waitlist_for(cat_id, open_at)
        closed_at = datetime(2026, 9, 1, tzinfo=UTC)
        assert not c.accepts_submissions_for(cat_id, closed_at)
        assert c.accepts_waitlist_for(cat_id, closed_at)
        assert c.is_any_nomination_waitlisting(closed_at)

    def test_early_stop_opens_the_waitlist_too(self) -> None:
        # Stopping early is closing by another route; the list does not care which.
        c, cat_id = _published()
        c.schedule_nomination_registration(category_id=cat_id, closes_at=datetime(2026, 12, 31, tzinfo=UTC), now=NOW)
        c.enable_nomination_waitlist(category_id=cat_id, now=NOW)
        at = datetime(2026, 8, 15, tzinfo=UTC)
        assert not c.accepts_waitlist_for(cat_id, at)
        c.stop_nomination_registration(category_id=cat_id, now=NOW)
        assert c.accepts_waitlist_for(cat_id, at)

    def test_disable_closes_the_list(self) -> None:
        c, cat_id = _published()
        c.enable_nomination_waitlist(category_id=cat_id, now=NOW)
        at = datetime(2026, 9, 1, tzinfo=UTC)
        assert c.accepts_waitlist_for(cat_id, at)
        disabled = c.disable_nomination_waitlist(category_id=cat_id, now=NOW)
        assert isinstance(disabled[0], NominationWaitlistDisabled)
        assert not c.accepts_waitlist_for(cat_id, at)

    def test_waitlist_gated_by_competition_status(self) -> None:
        # A closed nomination of a finished festival has no queue to join.
        fx = _configured()
        c = fx.competition
        c.enable_nomination_waitlist(category_id=fx.category_id, now=NOW)
        at = datetime(2026, 9, 1, tzinfo=UTC)
        assert not c.accepts_waitlist_for(fx.category_id, at)  # DRAFT
        c.mark_configured(now=NOW)
        c.mark_ready(now=NOW)
        c.publish(now=NOW)
        assert c.accepts_waitlist_for(fx.category_id, at)  # PUBLISHED
        c.start(now=NOW)
        assert c.accepts_waitlist_for(fx.category_id, at)  # RUNNING
        c.complete(now=NOW)
        assert not c.accepts_waitlist_for(fx.category_id, at)  # COMPLETED

    def test_waitlist_control_refused_after_complete(self) -> None:
        c = _completed()
        with pytest.raises(CompetitionAlreadyCompletedError):
            c.enable_nomination_waitlist(category_id=CategoryId.generate(), now=NOW)

    def test_waitlist_unknown_nomination_rejected(self) -> None:
        c = _draft()
        with pytest.raises(CategoryNotFoundError):
            c.enable_nomination_waitlist(category_id=CategoryId.generate(), now=NOW)


class TestContacts:
    def test_first_contact_becomes_primary(self) -> None:
        c = _draft()
        cid = ContactId.generate()
        events = c.add_contact(contact_id=cid, contact_type=ContactType.EMAIL, value=ContactValue("a@b.co"), now=NOW)
        assert isinstance(events[0], CompetitionContactAdded)
        assert c.primary_contact is not None
        assert c.primary_contact.id == cid

    def test_exactly_one_primary(self) -> None:
        c = _draft()
        a = ContactId.generate()
        b = ContactId.generate()
        c.add_contact(contact_id=a, contact_type=ContactType.EMAIL, value=ContactValue("a@b.co"), now=NOW)
        c.add_contact(contact_id=b, contact_type=ContactType.PHONE, value=ContactValue("+7900"), now=NOW, is_primary=True)
        primaries = [ct for ct in c.contacts if ct.is_primary]
        assert len(primaries) == 1
        assert primaries[0].id == b

    def test_duplicate_contact_rejected(self) -> None:
        c = _draft()
        c.add_contact(contact_id=ContactId.generate(), contact_type=ContactType.EMAIL, value=ContactValue("a@b.co"), now=NOW)
        with pytest.raises(DuplicateContactError):
            c.add_contact(contact_id=ContactId.generate(), contact_type=ContactType.EMAIL, value=ContactValue("a@b.co"), now=NOW)

    def test_remove_primary_promotes_another(self) -> None:
        c = _draft()
        a = ContactId.generate()
        b = ContactId.generate()
        c.add_contact(contact_id=a, contact_type=ContactType.EMAIL, value=ContactValue("a@b.co"), now=NOW)  # primary
        c.add_contact(contact_id=b, contact_type=ContactType.PHONE, value=ContactValue("+7900"), now=NOW)
        events = c.remove_contact(contact_id=a, now=NOW)
        assert isinstance(events[0], CompetitionContactRemoved)
        assert c.primary_contact is not None
        assert c.primary_contact.id == b

    def test_set_primary_contact(self) -> None:
        c = _draft()
        a = ContactId.generate()
        b = ContactId.generate()
        c.add_contact(contact_id=a, contact_type=ContactType.EMAIL, value=ContactValue("a@b.co"), now=NOW)
        c.add_contact(contact_id=b, contact_type=ContactType.PHONE, value=ContactValue("+7900"), now=NOW)
        c.set_primary_contact(contact_id=b, now=NOW)
        assert c.primary_contact is not None and c.primary_contact.id == b
        assert len([ct for ct in c.contacts if ct.is_primary]) == 1

    def test_remove_missing_contact_raises(self) -> None:
        with pytest.raises(ContactNotFoundError):
            _draft().remove_contact(contact_id=ContactId.generate(), now=NOW)


class TestInformationBlocks:
    def test_add_and_duplicate_title_rejected(self) -> None:
        c = _draft()
        c.add_information_block(
            block_id=InformationBlockId.generate(),
            title=InformationBlockTitle("Accommodation"),
            content=RichText("Hotels nearby"),
            now=NOW,
        )
        with pytest.raises(DuplicateInformationBlockError):
            c.add_information_block(
                block_id=InformationBlockId.generate(),
                title=InformationBlockTitle("Accommodation"),
                content=RichText("dup"),
                now=NOW,
            )

    def test_publish_and_hide_emit_events(self) -> None:
        c = _draft()
        bid = InformationBlockId.generate()
        c.add_information_block(block_id=bid, title=InformationBlockTitle("FAQ"), content=RichText("Q/A"), now=NOW)
        pub = c.publish_information_block(block_id=bid, now=NOW)
        assert isinstance(pub[0], CompetitionInformationPublished)
        assert c.information_blocks[0].is_published
        # idempotent publish
        assert c.publish_information_block(block_id=bid, now=NOW) == []
        hide = c.hide_information_block(block_id=bid, now=NOW)
        assert isinstance(hide[0], CompetitionInformationHidden)
        assert not c.information_blocks[0].is_published


class TestBranding:
    def test_update_branding_event_and_properties(self) -> None:
        c = _draft()
        events = c.update_branding(
            logo=FileReference("s3://logo.png"),
            banner=FileReference("s3://banner.png"),
            poster=FileReference("s3://poster.png"),
            now=NOW,
        )
        assert isinstance(events[0], CompetitionBrandingChanged)
        assert c.logo == FileReference("s3://logo.png")
        assert c.banner == FileReference("s3://banner.png")
        assert c.poster == FileReference("s3://poster.png")
        assert c.branding.poster == FileReference("s3://poster.png")

    def test_general_information_update_preserves_poster(self) -> None:
        c = _draft()
        c.update_branding(poster=FileReference("s3://poster.png"), now=NOW)
        c.update_general_information(
            now=NOW,
            title=CompetitionTitle("Renamed"),
            season=Season("2026/2027"),
            logo=FileReference("s3://logo2.png"),
        )
        assert c.logo == FileReference("s3://logo2.png")
        assert c.poster == FileReference("s3://poster.png")  # preserved
