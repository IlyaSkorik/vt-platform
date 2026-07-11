"""Tests for the Public Festival Catalog read model.

Two layers:

* pure projection rules (status mapping, mode classification, pricing, cover
  resolution) — exercised without a database, and
* the ORM-backed :class:`DjangoPublicCatalogReader` end to end on the in-memory
  SQLite test database, asserting which lifecycle states surface and how rows are
  projected and ordered.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.competitions.application.read_models import (
    PUBLIC_CATALOG_DOMAIN_STATUSES,
    ParticipationMode,
    aggregate_pricing,
    classify_participation_mode,
    public_status_for,
    resolve_city,
    resolve_cover_image,
)

# ---------------------------------------------------------------------------
# Pure projection rules
# ---------------------------------------------------------------------------


class TestPublicStatusProjection:
    def test_public_statuses_are_exactly_the_showcase_states(self) -> None:
        assert set(PUBLIC_CATALOG_DOMAIN_STATUSES) == {
            "PUBLISHED",
            "REGISTRATION_OPEN",
            "REGISTRATION_CLOSED",
            "RUNNING",
            "COMPLETED",
        }

    @pytest.mark.parametrize(
        ("domain_status", "expected"),
        [
            ("PUBLISHED", "COMING_SOON"),
            ("REGISTRATION_OPEN", "REGISTRATION_OPEN"),
            ("REGISTRATION_CLOSED", "REGISTRATION_CLOSED"),
            ("RUNNING", "RUNNING"),
            ("COMPLETED", "COMPLETED"),
        ],
    )
    def test_maps_public_states(self, domain_status: str, expected: str) -> None:
        assert public_status_for(domain_status) == expected

    @pytest.mark.parametrize("hidden", ["DRAFT", "CONFIGURED", "READY", "ARCHIVED"])
    def test_hidden_states_never_map(self, hidden: str) -> None:
        assert public_status_for(hidden) is None
        assert hidden not in PUBLIC_CATALOG_DOMAIN_STATUSES


class TestModeClassification:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Очное выступление", ParticipationMode.IN_PERSON),
            ("Оффлайн", ParticipationMode.IN_PERSON),
            ("Онлайн", ParticipationMode.ONLINE),
            ("Заочное участие", ParticipationMode.ONLINE),  # "заочн" → ONLINE, not IN_PERSON
            ("Видеовизитка", ParticipationMode.ONLINE),
            ("Гибридный формат", ParticipationMode.HYBRID),
            ("Hybrid", ParticipationMode.HYBRID),
        ],
    )
    def test_classifies_known_names(self, name: str, expected: ParticipationMode) -> None:
        assert classify_participation_mode(name) == expected

    @pytest.mark.parametrize("name", ["", "   ", "Гала-концерт", "Special"])
    def test_unrecognized_names_yield_none(self, name: str) -> None:
        assert classify_participation_mode(name) is None


class TestPricingAggregation:
    def test_empty_rules(self) -> None:
        pricing = aggregate_pricing([])
        assert pricing.amount_from is None
        assert pricing.currency is None
        assert pricing.multiple is False

    def test_single_price(self) -> None:
        pricing = aggregate_pricing([(Decimal("50.00"), "BYN")])
        assert pricing.amount_from == Decimal("50.00")
        assert pricing.currency == "BYN"
        assert pricing.multiple is False

    def test_multiple_prices_pick_cheapest_and_flag(self) -> None:
        pricing = aggregate_pricing(
            [(Decimal("80.00"), "BYN"), (Decimal("30.00"), "BYN"), (Decimal("55.00"), "BYN")]
        )
        assert pricing.amount_from == Decimal("30.00")
        assert pricing.currency == "BYN"
        assert pricing.multiple is True

    def test_currency_follows_cheapest_rule(self) -> None:
        pricing = aggregate_pricing([(Decimal("100.00"), "RUB"), (Decimal("20.00"), "BYN")])
        assert pricing.amount_from == Decimal("20.00")
        assert pricing.currency == "BYN"


class TestCoverResolution:
    def test_prefers_landing_hero_cover(self) -> None:
        config = {"blocks": [{"type": "HERO", "cover_image": "/media/hero.jpg"}]}
        assert resolve_cover_image(config, poster="/p.jpg", banner="/b.jpg") == "/media/hero.jpg"

    def test_falls_back_to_poster_then_banner(self) -> None:
        assert resolve_cover_image({}, poster="/p.jpg", banner="/b.jpg") == "/p.jpg"
        assert resolve_cover_image(None, poster=None, banner="/b.jpg") == "/b.jpg"

    def test_none_when_nothing_configured(self) -> None:
        assert resolve_cover_image({"blocks": []}, poster=None, banner=None) is None

    def test_ignores_blank_hero_cover(self) -> None:
        config = {"blocks": [{"type": "HERO", "cover_image": "  "}]}
        assert resolve_cover_image(config, poster="/p.jpg", banner=None) == "/p.jpg"


class TestCityResolution:
    def test_reads_city_from_contacts_venue_details(self) -> None:
        config = {"venue_details": {"city": "Минск"}}
        assert resolve_city(config) == "Минск"

    def test_none_when_absent_blank_or_malformed(self) -> None:
        assert resolve_city(None) is None
        assert resolve_city({}) is None
        assert resolve_city({"venue_details": {"city": "  "}}) is None
        assert resolve_city({"venue_details": "oops"}) is None


# ---------------------------------------------------------------------------
# ORM-backed reader (in-memory SQLite)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDjangoPublicCatalogReader:
    @staticmethod
    def _organization(name: str = "Дом талантов"):
        from apps.organization.infrastructure.models import OrganizationModel

        return OrganizationModel.objects.create(name=name, slug="dom-talantov")

    @staticmethod
    def _competition(*, organizer_id, status: str, title: str, **extra):
        from apps.competitions.infrastructure.models import CompetitionModel

        return CompetitionModel.objects.create(
            organizer_id=organizer_id,
            status=status,
            title=title,
            season="2025/2026",
            **extra,
        )

    def _reader(self):
        from apps.competitions.composition import build_public_catalog_read_service

        return build_public_catalog_read_service()

    def test_returns_only_publicly_visible_states(self) -> None:
        org = self._organization()
        visible = ["PUBLISHED", "REGISTRATION_OPEN", "REGISTRATION_CLOSED", "RUNNING", "COMPLETED"]
        hidden = ["DRAFT", "CONFIGURED", "READY", "ARCHIVED"]
        for state in visible + hidden:
            self._competition(organizer_id=org.id, status=state, title=f"Fest {state}")

        festivals = self._reader().list_festivals()

        titles = {festival.title for festival in festivals}
        assert titles == {f"Fest {state}" for state in visible}

    def test_maps_status_and_organizer_name(self) -> None:
        org = self._organization(name="Дом талантов")
        self._competition(organizer_id=org.id, status="PUBLISHED", title="Скоро")

        [festival] = self._reader().list_festivals()

        assert festival.status == "COMING_SOON"
        assert festival.organizer.name == "Дом талантов"
        assert festival.organizer.logo is None

    def test_unknown_organizer_gets_fallback_name(self) -> None:
        import uuid

        self._competition(organizer_id=uuid.uuid4(), status="RUNNING", title="Сиротский фестиваль")

        [festival] = self._reader().list_festivals()

        assert festival.organizer.name == "Организатор"

    def test_projects_formats_modes_pricing_and_categories(self) -> None:
        from apps.competitions.infrastructure.models import (
            CategoryModel,
            ParticipationFormatModel,
            PricingRuleModel,
        )

        org = self._organization()
        competition = self._competition(
            organizer_id=org.id,
            status="REGISTRATION_OPEN",
            title="Весенний вокал",
            venue_name="Дворец культуры",
            contacts_config={"venue_details": {"city": "Минск"}},
        )
        ParticipationFormatModel.objects.create(competition=competition, name="Очно", sort_order=0)
        ParticipationFormatModel.objects.create(competition=competition, name="Онлайн", sort_order=1)
        ParticipationFormatModel.objects.create(
            competition=competition, name="Скрытый", enabled=False, sort_order=2
        )
        CategoryModel.objects.create(competition=competition, name="Вокал", sort_order=0)
        import uuid

        for amount in ("30.00", "75.00"):
            PricingRuleModel.objects.create(
                competition=competition,
                category_id=uuid.uuid4(),
                discipline_id=uuid.uuid4(),
                age_category_id=uuid.uuid4(),
                participant_group_id=uuid.uuid4(),
                participation_format_id=uuid.uuid4(),
                amount=Decimal(amount),
                currency="BYN",
            )

        [festival] = self._reader().list_festivals()

        assert festival.city == "Минск"
        assert [fmt.name for fmt in festival.formats] == ["Очно", "Онлайн"]  # disabled excluded
        assert festival.modes == ["IN_PERSON", "ONLINE"]
        assert festival.pricing.amount_from == Decimal("30.00")
        assert festival.pricing.multiple is True
        assert festival.categories == ["Вокал"]

    def test_orders_newest_first(self) -> None:
        org = self._organization()
        first = self._competition(organizer_id=org.id, status="COMPLETED", title="Старый")
        second = self._competition(organizer_id=org.id, status="COMPLETED", title="Новый")
        # Force a deterministic ordering on created_at.
        from datetime import timedelta

        from django.utils import timezone

        from apps.competitions.infrastructure.models import CompetitionModel

        now = timezone.now()
        CompetitionModel.objects.filter(pk=first.pk).update(created_at=now - timedelta(days=2))
        CompetitionModel.objects.filter(pk=second.pk).update(created_at=now)

        festivals = self._reader().list_festivals()

        assert [festival.title for festival in festivals] == ["Новый", "Старый"]

    def test_empty_catalog(self) -> None:
        assert self._reader().list_festivals() == []
