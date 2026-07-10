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
    CompetitionCreated,
    CompetitionDeadlineChanged,
    CompetitionInformationHidden,
    CompetitionInformationPublished,
    CompetitionPublished,
    CompetitionRegistrationClosed,
    CompetitionRegistrationOpened,
    CompetitionSettingsChanged,
    CompetitionStarted,
    ParticipationFormatDisabled,
    ParticipationFormatEnabled,
    PricingRuleAdded,
    PricingRuleRemoved,
    RegulationPublished,
)
from apps.competitions.domain.exceptions import (
    AdmissionRuleInUseError,
    AdmissionRuleNotFoundError,
    CategoryInUseError,
    CompetitionAlreadyArchivedError,
    ConfigurationLockedError,
    ContactNotFoundError,
    DirectConstructionError,
    DisciplineCategoryMismatchError,
    DuplicateAdmissionRuleError,
    DuplicateCategoryError,
    DuplicateContactError,
    DuplicateDisciplineError,
    DuplicateInformationBlockError,
    DuplicatePricingRuleError,
    IllegalStatusTransitionError,
    OverlappingAgeRangeError,
    OverlappingParticipantRangeError,
    ParticipationFormatNotEnabledError,
    PublicationRequirementsNotMetError,
    RegulationNotFoundError,
    ServiceNotFoundError,
)
from apps.competitions.domain.value_objects import (
    AdmissionCombination,
    AgeCategoryId,
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
    Money,
    OrganizerId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantGroupName,
    ParticipationFormat,
    PublicationIssueCode,
    RegistrationDeadlines,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    RichText,
    Season,
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
    age = c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(6, 8), now=NOW)
    grp = c.add_participant_group(
        participant_group_id=ParticipantGroupId.generate(),
        category_id=cat.id,
        name=ParticipantGroupName("Solo"),
        count_range=ParticipantCountRange(1, 1),
        now=NOW,
    )
    c.enable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW)
    c.enable_format(participation_format=ParticipationFormat.ONLINE, now=NOW)
    offline = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.OFFLINE)
    online = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.ONLINE)
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
        c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(6, 8), now=NOW)
        with pytest.raises(OverlappingAgeRangeError):
            c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(8, 10), now=NOW)

    def test_non_overlapping_age_range_allowed(self) -> None:
        c = _draft()
        c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(6, 8), now=NOW)
        c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(9, 11), now=NOW)
        assert len(c.age_categories) == 2

    def test_overlapping_participant_range_within_category_rejected(self) -> None:
        c = _draft()
        cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            category_id=cat.id,
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        with pytest.raises(OverlappingParticipantRangeError):
            c.add_participant_group(
                participant_group_id=ParticipantGroupId.generate(),
                category_id=cat.id,
                name=ParticipantGroupName("Duet"),
                count_range=ParticipantCountRange(1, 2),
                now=NOW,
            )

    def test_same_participant_range_allowed_in_different_category(self) -> None:
        c = _draft()
        a = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        b = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Dance"), now=NOW)
        rng = ParticipantCountRange(1, 1)
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(), category_id=a.id, name=ParticipantGroupName("Solo"), count_range=rng, now=NOW
        )
        c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(), category_id=b.id, name=ParticipantGroupName("Solo"), count_range=rng, now=NOW
        )
        assert len(c.participant_groups) == 2


class TestAdmissionAndPricing:
    def test_admission_rule_added_event(self) -> None:
        fx = _configured(priced=False)
        c = _draft()
        cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        disc = c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
        age = c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(6, 8), now=NOW)
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            category_id=cat.id,
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        c.enable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW)
        combo = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.OFFLINE)
        events = c.add_admission_rule(combination=combo, now=NOW)
        assert isinstance(events[0], AdmissionRuleAdded)
        assert c.is_admissible(combo)
        assert fx.competition.is_admissible(fx.offline)

    def test_discipline_category_mismatch_rejected(self) -> None:
        fx = _configured()
        other_cat = fx.competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Dance"), now=NOW)
        bad = AdmissionCombination(other_cat.id, fx.discipline_id, fx.age_id, fx.group_id, ParticipationFormat.OFFLINE)
        with pytest.raises(DisciplineCategoryMismatchError):
            fx.competition.add_admission_rule(combination=bad, now=NOW)

    def test_format_not_enabled_rejected(self) -> None:
        c = _draft()
        cat = c.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=NOW)
        disc = c.add_discipline(discipline_id=DisciplineId.generate(), category_id=cat.id, name=DisciplineName("Pop"), now=NOW)
        age = c.add_age_category(age_category_id=AgeCategoryId.generate(), age_range=AgeRange(6, 8), now=NOW)
        grp = c.add_participant_group(
            participant_group_id=ParticipantGroupId.generate(),
            category_id=cat.id,
            name=ParticipantGroupName("Solo"),
            count_range=ParticipantCountRange(1, 1),
            now=NOW,
        )
        combo = AdmissionCombination(cat.id, disc.id, age.id, grp.id, ParticipationFormat.OFFLINE)
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
    def test_enable_disable_events(self) -> None:
        c = _draft()
        enabled = c.enable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW)
        assert isinstance(enabled[0], ParticipationFormatEnabled)
        assert c.enable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW) == []  # idempotent
        disabled = c.disable_format(participation_format=ParticipationFormat.OFFLINE, now=NOW)
        assert isinstance(disabled[0], ParticipationFormatDisabled)


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

    def test_missing_price_is_error(self) -> None:
        fx = _configured(priced=False)
        report = fx.competition.publication_report()
        assert PublicationIssueCode.MISSING_PRICING_RULES in {i.code for i in report.errors}

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
        assert isinstance(c.open_registration(now=NOW)[0], CompetitionRegistrationOpened)
        assert c.is_registration_open()
        assert isinstance(c.close_registration(now=NOW)[0], CompetitionRegistrationClosed)
        assert isinstance(c.start(now=NOW)[0], CompetitionStarted)
        assert isinstance(c.complete(now=NOW)[0], CompetitionCompleted)
        assert str(c.status) == "COMPLETED"

    def test_illegal_transition_publish_from_draft(self) -> None:
        fx = _configured()
        with pytest.raises(IllegalStatusTransitionError):
            fx.competition.publish(now=NOW)  # still DRAFT, not READY

    def test_illegal_transition_open_registration_from_draft(self) -> None:
        with pytest.raises(IllegalStatusTransitionError):
            _draft().open_registration(now=NOW)

    def test_mark_ready_refused_when_incomplete(self) -> None:
        c = _draft()
        c.mark_configured(now=NOW)
        with pytest.raises(PublicationRequirementsNotMetError):
            c.mark_ready(now=NOW)

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

    def test_archive_from_any_state_and_immutable(self) -> None:
        fx = _configured()
        fx.competition.archive(now=NOW)
        assert fx.competition.is_archived()
        with pytest.raises(CompetitionAlreadyArchivedError):
            fx.competition.archive(now=NOW)
        with pytest.raises(CompetitionAlreadyArchivedError):
            fx.competition.add_document(
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
    def test_add_service_fixed_price_and_event(self) -> None:
        c = _draft()
        sid = ServiceId.generate()
        events = c.add_additional_service(service_id=sid, name=ServiceName("Medal"), price=Money.of("500"), now=NOW)
        assert isinstance(events[0], AdditionalServiceAdded)
        (service,) = c.additional_services
        assert service.price == Money.of("500")
        assert service.is_enabled

    def test_enable_disable_update_remove(self) -> None:
        c = _draft()
        sid = ServiceId.generate()
        c.add_additional_service(service_id=sid, name=ServiceName("Video"), price=Money.of("1000"), now=NOW)
        c.disable_additional_service(service_id=sid, now=NOW)
        assert not c.additional_services[0].is_enabled
        c.enable_additional_service(service_id=sid, now=NOW)
        assert c.additional_services[0].is_enabled
        c.update_additional_service(service_id=sid, name=ServiceName("Pro Video"), price=Money.of("1200"), description=None, now=NOW)
        assert c.additional_services[0].name == ServiceName("Pro Video")
        c.remove_additional_service(service_id=sid, now=NOW)
        assert c.additional_services == ()

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
        assert payload["currency"] == "RUB"
        assert isinstance(payload["category_id"], str)


class TestSettings:
    def test_default_settings_present(self) -> None:
        assert _draft().settings == CompetitionSettings.default()

    def test_update_settings_emits_event(self) -> None:
        c = _draft()
        new = CompetitionSettings.default().with_changes(require_parent_consent=True, allow_multiple_applications=True)
        events = c.update_settings(settings=new, now=NOW)
        assert isinstance(events[0], CompetitionSettingsChanged)
        assert c.settings.require_parent_consent is True
        assert c.settings.allow_multiple_applications is True

    def test_settings_locked_after_archive(self) -> None:
        c = _draft()
        c.archive(now=NOW)
        with pytest.raises(CompetitionAlreadyArchivedError):
            c.update_settings(settings=CompetitionSettings.default(), now=NOW)


class TestDeadlines:
    def test_update_deadlines_and_queries(self) -> None:
        c = _draft()
        deadline = datetime(2026, 8, 1, tzinfo=UTC)
        events = c.update_deadlines(deadlines=RegistrationDeadlines(application=deadline, music_upload=deadline), now=NOW)
        assert isinstance(events[0], CompetitionDeadlineChanged)
        assert c.is_application_allowed(datetime(2026, 7, 15, tzinfo=UTC))
        assert not c.is_application_allowed(datetime(2026, 8, 2, tzinfo=UTC))
        assert c.is_music_upload_allowed(datetime(2026, 7, 15, tzinfo=UTC))
        # No payment deadline set -> always allowed (until archived).
        assert c.is_payment_allowed(datetime(2030, 1, 1, tzinfo=UTC))

    def test_all_disallowed_when_archived(self) -> None:
        c = _draft()
        c.archive(now=NOW)
        assert not c.is_application_allowed(NOW)
        assert not c.is_payment_allowed(NOW)
        assert not c.is_music_upload_allowed(NOW)


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
