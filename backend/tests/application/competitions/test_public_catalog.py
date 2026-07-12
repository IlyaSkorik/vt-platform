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
    resolve_landing_cover,
    resolve_poster_image,
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
        pricing = aggregate_pricing([(Decimal("80.00"), "BYN"), (Decimal("30.00"), "BYN"), (Decimal("55.00"), "BYN")])
        assert pricing.amount_from == Decimal("30.00")
        assert pricing.currency == "BYN"
        assert pricing.multiple is True

    def test_currency_follows_cheapest_rule(self) -> None:
        pricing = aggregate_pricing([(Decimal("100.00"), "RUB"), (Decimal("20.00"), "BYN")])
        assert pricing.amount_from == Decimal("20.00")
        assert pricing.currency == "BYN"


class TestPosterResolution:
    def test_prefers_poster_over_banner(self) -> None:
        assert resolve_poster_image("/p.jpg", "/b.jpg") == "/p.jpg"

    def test_falls_back_to_banner_when_no_poster(self) -> None:
        assert resolve_poster_image(None, "/b.jpg") == "/b.jpg"
        assert resolve_poster_image("  ", "/b.jpg") == "/b.jpg"

    def test_none_when_neither_set(self) -> None:
        assert resolve_poster_image(None, None) is None


class TestLandingCoverResolution:
    def test_reads_hero_block_cover(self) -> None:
        config = {"blocks": [{"type": "HERO", "cover_image": "/media/hero.jpg"}]}
        assert resolve_landing_cover(config) == "/media/hero.jpg"

    def test_none_when_no_hero_cover(self) -> None:
        assert resolve_landing_cover({"blocks": []}) is None
        assert resolve_landing_cover(None) is None
        assert resolve_landing_cover({"blocks": [{"type": "HERO", "cover_image": "  "}]}) is None


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
        ParticipationFormatModel.objects.create(competition=competition, name="Скрытый", enabled=False, sort_order=2)
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


# ---------------------------------------------------------------------------
# Landing & contacts projections (pure)
# ---------------------------------------------------------------------------


class TestLandingProjection:
    def test_default_config_projects_only_enabled_blocks_in_order(self) -> None:
        from apps.competitions.application.read_models import project_landing
        from apps.competitions.domain.landing_configuration import LandingConfiguration

        landing = project_landing(LandingConfiguration.default())

        # HERO + REGULATION + DOCUMENTS + VENUE ship enabled by default.
        assert [block.type for block in landing.blocks] == [
            "HERO",
            "REGULATION",
            "DOCUMENTS",
            "VENUE",
        ]
        assert [block.sort_order for block in landing.blocks] == [0, 1, 2, 3]

    def test_projects_content_jury_partners_and_sorts_children(self) -> None:
        from apps.competitions.application.read_models import project_landing
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_HERO_ID,
            SYSTEM_BLOCK_VENUE_ID,
            JuryCard,
            LandingBlock,
            LandingBlockType,
            LandingConfiguration,
        )

        content = LandingBlock(
            id="01900000-0000-7000-8000-0000000000a1",
            type=LandingBlockType.CONTENT,
            enabled=True,
            sort_order=2,
            title="Про фестиваль",
            body="Программа",
        )
        jury = LandingBlock(
            id="01900000-0000-7000-8000-0000000000a2",
            type=LandingBlockType.JURY,
            enabled=True,
            sort_order=3,
            cards=(
                JuryCard(id="01900000-0000-7000-8000-0000000000b2", name="Второй", sort_order=1),
                JuryCard(id="01900000-0000-7000-8000-0000000000b1", name="Первый", sort_order=0),
            ),
        )
        hidden = LandingBlock(
            id="01900000-0000-7000-8000-0000000000a3",
            type=LandingBlockType.FAQ,
            enabled=False,
            sort_order=4,
        )
        config = LandingConfiguration(
            blocks=(
                LandingBlock(
                    id=SYSTEM_BLOCK_HERO_ID,
                    type=LandingBlockType.HERO,
                    enabled=True,
                    sort_order=0,
                    title="Заголовок",
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_VENUE_ID,
                    type=LandingBlockType.VENUE,
                    enabled=True,
                    sort_order=1,
                ),
                content,
                jury,
                hidden,
            )
        )

        landing = project_landing(config)

        assert [block.type for block in landing.blocks] == ["HERO", "VENUE", "CONTENT", "JURY"]
        content_view = landing.blocks[2]
        assert content_view.title == "Про фестиваль"
        assert content_view.body == "Программа"
        jury_view = landing.blocks[3]
        assert [card.name for card in jury_view.jury] == ["Первый", "Второй"]


class TestContactsProjection:
    def test_prefers_override_name_and_merges_venue(self) -> None:
        from apps.competitions.application.read_models import project_contacts
        from apps.competitions.domain.contacts_configuration import (
            ContactProfileOverride,
            ContactsConfiguration,
            TeamContact,
            VenueDetails,
        )

        config = ContactsConfiguration(
            override=ContactProfileOverride(
                organization_name="Оргкомитет фестиваля",
                phone="+375291234567",
                website="https://fest.by",
                vk="https://vk.com/fest",
            ),
            team_contacts=(
                TeamContact(id="01900000-0000-7000-8000-0000000000c2", name="Женя", sort_order=1),
                TeamContact(id="01900000-0000-7000-8000-0000000000c1", name="Дина", sort_order=0),
            ),
            venue_details=VenueDetails(city="Минск", google_maps_url="https://maps.example/x"),
        )

        contacts = project_contacts(
            config,
            organizer_name="Дом талантов",
            venue_name="Дворец культуры",
            venue_address="ул. Ленина, 1",
        )

        assert contacts.organization_name == "Оргкомитет фестиваля"
        assert contacts.phone == "+375291234567"
        assert contacts.website == "https://fest.by"
        assert contacts.social.vk == "https://vk.com/fest"
        assert [member.name for member in contacts.team] == ["Дина", "Женя"]
        assert contacts.venue.name == "Дворец культуры"
        assert contacts.venue.city == "Минск"
        assert contacts.venue.has_content is True

    def test_falls_back_to_organizer_name(self) -> None:
        from apps.competitions.application.read_models import project_contacts
        from apps.competitions.domain.contacts_configuration import ContactsConfiguration

        contacts = project_contacts(
            ContactsConfiguration.default(),
            organizer_name="Дом талантов",
            venue_name=None,
            venue_address=None,
        )

        assert contacts.organization_name == "Дом талантов"
        assert contacts.venue.has_content is False


# ---------------------------------------------------------------------------
# ORM-backed reader — get_festival (detail)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDjangoPublicCatalogReaderDetail:
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

    def test_returns_detail_with_landing_and_contacts(self) -> None:
        org = self._organization(name="Дом талантов")
        competition = self._competition(
            organizer_id=org.id,
            status="REGISTRATION_OPEN",
            title="Весенний вокал",
            venue_name="Дворец культуры",
            contacts_config={
                "override": {"organization_name": "Оргкомитет", "email": "hi@fest.by"},
                "venue_details": {"city": "Минск"},
            },
        )

        detail = self._reader().get_festival(str(competition.id))

        assert detail is not None
        assert detail.status == "REGISTRATION_OPEN"
        # Default landing config seeds enabled HERO + REGULATION + DOCUMENTS + VENUE.
        assert [block.type for block in detail.landing.blocks] == [
            "HERO",
            "REGULATION",
            "DOCUMENTS",
            "VENUE",
        ]
        assert detail.contacts.organization_name == "Оргкомитет"
        assert detail.contacts.email == "hi@fest.by"
        assert detail.contacts.venue.name == "Дворец культуры"
        assert detail.contacts.venue.city == "Минск"

    def test_card_uses_poster_landing_uses_hero_cover(self) -> None:
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_HERO_ID,
            SYSTEM_BLOCK_VENUE_ID,
        )

        org = self._organization()
        competition = self._competition(
            organizer_id=org.id,
            status="RUNNING",
            title="Проверка изображений",
            poster="/media/afisha.jpg",
            banner="/media/banner.jpg",
            landing_config={
                "blocks": [
                    {
                        "id": SYSTEM_BLOCK_HERO_ID,
                        "type": "HERO",
                        "enabled": True,
                        "sort_order": 0,
                        "cover_image": "/media/cover.jpg",
                    },
                    {"id": SYSTEM_BLOCK_VENUE_ID, "type": "VENUE", "enabled": True, "sort_order": 1},
                ]
            },
        )

        detail = self._reader().get_festival(str(competition.id))
        [card] = self._reader().list_festivals()

        assert detail is not None
        assert card.cover_image == "/media/afisha.jpg"  # Афиша — на карточке каталога
        assert detail.cover_image == "/media/cover.jpg"  # Обложка — на лендинге

    def _with_regulation(self, competition):
        import datetime

        from apps.competitions.infrastructure.models import CompetitionModel, RegulationModel

        regulation = RegulationModel.objects.create(
            competition=competition,
            title="Положение",
            document_version="v1",
            publication_date=datetime.date(2026, 5, 1),
            file_reference="/media/reg.pdf",
        )
        CompetitionModel.objects.filter(pk=competition.pk).update(
            current_regulation_id=regulation.id
        )

    def test_default_config_shows_regulation_block(self) -> None:
        org = self._organization()
        competition = self._competition(organizer_id=org.id, status="RUNNING", title="Показ положения")
        self._with_regulation(competition)

        detail = self._reader().get_festival(str(competition.id))

        assert detail is not None
        assert "REGULATION" in [block.type for block in detail.landing.blocks]
        assert detail.regulation is not None

    def test_disabled_regulation_block_is_hidden(self) -> None:
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_HERO_ID,
            SYSTEM_BLOCK_REGULATION_ID,
            SYSTEM_BLOCK_VENUE_ID,
        )

        org = self._organization()
        competition = self._competition(
            organizer_id=org.id,
            status="RUNNING",
            title="Выключен",
            landing_config={
                "blocks": [
                    {"id": SYSTEM_BLOCK_HERO_ID, "type": "HERO", "enabled": True, "sort_order": 0},
                    {
                        "id": SYSTEM_BLOCK_REGULATION_ID,
                        "type": "REGULATION",
                        "enabled": False,
                        "sort_order": 1,
                    },
                    {"id": SYSTEM_BLOCK_VENUE_ID, "type": "VENUE", "enabled": True, "sort_order": 2},
                ]
            },
        )
        self._with_regulation(competition)

        detail = self._reader().get_festival(str(competition.id))

        assert detail is not None
        # Organizer disabled the block: it is respected even though a regulation exists.
        assert "REGULATION" not in [block.type for block in detail.landing.blocks]
        assert detail.regulation is not None

    def test_projects_only_public_published_documents(self) -> None:
        from apps.competitions.infrastructure.models import DocumentModel

        org = self._organization()
        competition = self._competition(
            organizer_id=org.id, status="RUNNING", title="Документный конкурс"
        )
        DocumentModel.objects.create(
            competition=competition,
            title="Программа",
            category="PROGRAM",
            visibility="PUBLIC",
            file_reference="/media/program.pdf",
            published=True,
            sort_order=1,
        )
        DocumentModel.objects.create(
            competition=competition,
            title="Для всех",
            category="OTHER",
            visibility="ALL",
            file_reference="/media/all.pdf",
            published=True,
            sort_order=0,
        )
        DocumentModel.objects.create(
            competition=competition,
            title="Только участникам",
            category="MEMO",
            visibility="PARTICIPANTS",
            file_reference="/media/memo.pdf",
            published=True,
            sort_order=2,
        )
        DocumentModel.objects.create(
            competition=competition,
            title="Черновик",
            category="OTHER",
            visibility="PUBLIC",
            file_reference="/media/draft.pdf",
            published=False,
            sort_order=3,
        )

        detail = self._reader().get_festival(str(competition.id))

        assert detail is not None
        # PUBLIC + ALL, published only, sorted by sort_order; hidden ones excluded.
        assert [doc.title for doc in detail.documents] == ["Для всех", "Программа"]
        assert "DOCUMENTS" in [block.type for block in detail.landing.blocks]

    def test_injects_regulation_marker_for_legacy_config(self) -> None:
        from apps.competitions.domain.landing_configuration import (
            SYSTEM_BLOCK_HERO_ID,
            SYSTEM_BLOCK_VENUE_ID,
        )

        org = self._organization()
        competition = self._competition(
            organizer_id=org.id,
            status="RUNNING",
            title="Старый конфиг",
            landing_config={
                "blocks": [
                    {"id": SYSTEM_BLOCK_HERO_ID, "type": "HERO", "enabled": True, "sort_order": 0},
                    {"id": SYSTEM_BLOCK_VENUE_ID, "type": "VENUE", "enabled": True, "sort_order": 1},
                ]
            },
        )
        self._with_regulation(competition)

        detail = self._reader().get_festival(str(competition.id))

        assert detail is not None
        # Config predates the REGULATION block, so a marker is injected to keep it visible.
        assert "REGULATION" in [block.type for block in detail.landing.blocks]

    def test_none_for_hidden_state(self) -> None:
        org = self._organization()
        competition = self._competition(organizer_id=org.id, status="DRAFT", title="Черновик")

        assert self._reader().get_festival(str(competition.id)) is None

    def test_none_for_missing_and_malformed_id(self) -> None:
        import uuid

        assert self._reader().get_festival(str(uuid.uuid4())) is None
        assert self._reader().get_festival("not-a-uuid") is None
