"""The Public Festival Catalog read model.

A dedicated, denormalized projection powering the participant-facing catalog
(``GET /api/v1/public/festivals``). It is intentionally **separate** from the
organizer write API and the :class:`~apps.competitions.domain.entities.Competition`
aggregate: nothing here rehydrates the aggregate or enforces an invariant — it
reads persisted rows and shapes them for public display (ARCH-001 §7.2, §14,
CQRS read side).

Layering: this module is pure and framework-free. It defines

* the flat view DTOs the presentation edge serializes,
* the read-service **port** the composition root wires to a concrete adapter,
* and the pure projection rules — which lifecycle states are public, how each
  maps to a public status, how free-text participation formats are classified
  into display modes, how a "from" price is derived, and how a cover image is
  resolved.

The pure rules live here (not in the infrastructure adapter) so they are unit
tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from apps.competitions.domain.contacts_configuration import ContactsConfiguration
from apps.competitions.domain.landing_configuration import LandingBlock, LandingConfiguration

__all__ = [
    "PUBLIC_CATALOG_DOMAIN_STATUSES",
    "ParticipationMode",
    "PublicCatalogReadService",
    "PublicFestivalContactsView",
    "PublicFestivalDetailView",
    "PublicFestivalEmergencyView",
    "PublicFestivalFaqItemView",
    "PublicFestivalFormatView",
    "PublicFestivalGalleryImageView",
    "PublicFestivalJuryCardView",
    "PublicFestivalLandingBlockView",
    "PublicFestivalLandingView",
    "PublicFestivalOrganizerView",
    "PublicFestivalPartnerCardView",
    "PublicFestivalPricingView",
    "PublicFestivalRegulationView",
    "PublicFestivalSocialLinksView",
    "PublicFestivalTeamMemberView",
    "PublicFestivalVenueView",
    "PublicFestivalView",
    "aggregate_pricing",
    "classify_participation_mode",
    "project_contacts",
    "project_landing",
    "public_status_for",
    "resolve_city",
    "resolve_cover_image",
]


# --- Public status projection --------------------------------------------------
#
# The catalog is a public *showcase*, not merely a registration list: participants
# discover upcoming, live and past competitions, not only ones currently taking
# applications. So every published, publicly-visible lifecycle state is exposed —
# DRAFT / CONFIGURED / READY (pre-publication) and ARCHIVED (retired) are never
# surfaced. Each domain state maps to a coarse *public status* that tells the
# frontend which call-to-action to render.
_PUBLIC_STATUS_BY_DOMAIN: dict[str, str] = {
    "PUBLISHED": "COMING_SOON",  # published & frozen; registration not opened yet
    "REGISTRATION_OPEN": "REGISTRATION_OPEN",  # accepting applications → "Apply"
    "REGISTRATION_CLOSED": "REGISTRATION_CLOSED",  # window closed → "Registration closed"
    "RUNNING": "RUNNING",  # taking place → "In progress"
    "COMPLETED": "COMPLETED",  # finished → "Completed"
}

#: Domain lifecycle states a competition must be in to appear in the catalog.
#: Used verbatim as the read query's ``status__in`` filter.
PUBLIC_CATALOG_DOMAIN_STATUSES: tuple[str, ...] = tuple(_PUBLIC_STATUS_BY_DOMAIN)


def public_status_for(domain_status: str) -> str | None:
    """Map a domain :class:`CompetitionStatus` value to its public status.

    Returns ``None`` for states that must never be exposed (DRAFT, CONFIGURED,
    READY, ARCHIVED) so callers cannot accidentally leak them.
    """
    return _PUBLIC_STATUS_BY_DOMAIN.get(domain_status)


# --- Participation mode classification ----------------------------------------
#
# Organizers configure participation formats as free-text data (e.g. "Очное
# выступление", "Онлайн"), not a fixed enum — see ``ParticipationFormat``. The
# catalog nonetheless wants normalized IN_PERSON / ONLINE / HYBRID badges and
# filters, so we classify each format name by keyword. This is a heuristic ACL:
# the day the domain gains an explicit format-kind field, ``classify_participation_mode``
# is the single place that changes.
class ParticipationMode(StrEnum):
    """Normalized display mode a participation format resolves to."""

    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"


# Ordered most-specific first: "заочно" (correspondence) contains the substring
# "очн" but must classify as ONLINE, so ONLINE keywords are tested before IN_PERSON.
_HYBRID_KEYWORDS = ("гибрид", "hybrid", "смешан", "комбинир")
_ONLINE_KEYWORDS = ("онлайн", "online", "дистанц", "заочн", "remote", "видео", "video", "zoom")
_IN_PERSON_KEYWORDS = (
    "очно",
    "очн",
    "офлайн",
    "оффлайн",
    "offline",
    "in person",
    "in-person",
    "на месте",
    "live",
)


def classify_participation_mode(name: str) -> ParticipationMode | None:
    """Classify a free-text participation-format name into a display mode.

    Returns ``None`` when no keyword matches, so an unrecognized format never
    produces a misleading badge.
    """
    normalized = (name or "").strip().lower()
    if not normalized:
        return None
    if any(keyword in normalized for keyword in _HYBRID_KEYWORDS):
        return ParticipationMode.HYBRID
    if any(keyword in normalized for keyword in _ONLINE_KEYWORDS):
        return ParticipationMode.ONLINE
    if any(keyword in normalized for keyword in _IN_PERSON_KEYWORDS):
        return ParticipationMode.IN_PERSON
    return None


# --- Cover image resolution ---------------------------------------------------

_HERO_BLOCK_TYPE = "HERO"


def resolve_cover_image(
    landing_config: dict[str, object] | None,
    *,
    poster: str | None,
    banner: str | None,
) -> str | None:
    """Pick the best available cover reference for a catalog card.

    Preference order: the public landing page's hero image (the asset the
    organizer curated for the public face of the competition), then the poster,
    then the banner. Returns ``None`` when nothing is set.
    """
    hero_cover = _hero_cover_image(landing_config)
    for candidate in (hero_cover, poster, banner):
        value = (candidate or "").strip() if isinstance(candidate, str) else None
        if value:
            return value
    return None


def resolve_city(contacts_config: dict[str, object] | None) -> str | None:
    """Pick the host **city** for a catalog card.

    The city is a distinct fact configured on the competition's contacts
    (``contacts_config.venue_details.city``) — deliberately *not* the venue place
    name (``venue_name``), which is a hall/address, not a city. Returns ``None``
    when the organizer has not set a city.
    """
    if not isinstance(contacts_config, dict):
        return None
    venue_details = contacts_config.get("venue_details")
    if not isinstance(venue_details, dict):
        return None
    city = venue_details.get("city")
    if isinstance(city, str) and city.strip():
        return city.strip()
    return None


def _hero_cover_image(landing_config: dict[str, object] | None) -> str | None:
    if not isinstance(landing_config, dict):
        return None
    blocks = landing_config.get("blocks")
    if not isinstance(blocks, list):
        return None
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == _HERO_BLOCK_TYPE:
            cover = block.get("cover_image")
            if isinstance(cover, str) and cover.strip():
                return cover.strip()
    return None


# --- Pricing aggregation ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicFestivalPricingView:
    """The "from X" price summary shown on a catalog card.

    ``amount_from`` is the cheapest configured unit price; ``multiple`` is true
    when the competition has more than one distinct price, so the frontend can
    prefix "from". Both are absent (``None`` / ``False``) when no pricing exists.
    """

    amount_from: Decimal | None
    currency: str | None
    multiple: bool


def aggregate_pricing(rules: list[tuple[Decimal, str]]) -> PublicFestivalPricingView:
    """Derive the "from" price from a competition's pricing rules.

    Picks the minimum amount and the currency of that cheapest rule, and flags
    whether more than one distinct amount exists.
    """
    if not rules:
        return PublicFestivalPricingView(amount_from=None, currency=None, multiple=False)
    cheapest_amount, cheapest_currency = min(rules, key=lambda rule: rule[0])
    distinct_amounts = {amount for amount, _ in rules}
    return PublicFestivalPricingView(
        amount_from=cheapest_amount,
        currency=cheapest_currency,
        multiple=len(distinct_amounts) > 1,
    )


# --- View DTOs ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicFestivalOrganizerView:
    """The organizer identity rendered on a catalog card (context-local shape)."""

    id: str
    name: str
    logo: str | None = None


@dataclass(frozen=True, slots=True)
class PublicFestivalFormatView:
    """One participation format, with its normalized display mode (may be ``None``)."""

    name: str
    mode: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalView:
    """A single competition as seen in the public catalog — flat and serializable.

    Registration progress is intentionally absent: it depends on the Applications
    bounded context (not yet built) and no capacity is modelled, so there is no
    honest number to project. The frontend footer renders without it and gains it
    for free when Applications lands and this view grows a field.
    """

    id: str
    title: str
    season: str
    description: str | None
    status: str
    organizer: PublicFestivalOrganizerView
    city: str | None
    venue_name: str | None
    venue_address: str | None
    cover_image: str | None
    competition_start: date | None
    competition_end: date | None
    registration_start: date | None
    registration_end: date | None
    application_deadline: datetime | None
    pricing: PublicFestivalPricingView
    formats: list[PublicFestivalFormatView] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Landing-page projection --------------------------------------------------
#
# The public landing page renders the organizer-curated Landing Builder
# configuration. The catalog card only needs the hero cover; the landing page
# needs the full, ordered set of *enabled* blocks with their typed payloads. The
# projection below narrows the domain :class:`LandingConfiguration` value object
# (parsed by the infrastructure adapter from the persisted JSON) into flat,
# serializable view DTOs — dropping disabled blocks and sorting everything the
# same way the organizer configured it. The VENUE block carries no payload of its
# own: it is a positional marker telling the frontend where to render the shared
# venue/contacts data (Competition stays the single source of truth).


@dataclass(frozen=True, slots=True)
class PublicFestivalJuryCardView:
    """One jury/expert card in a landing JURY block."""

    id: str
    name: str
    photo: str | None
    position: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalPartnerCardView:
    """One partner/sponsor card in a landing PARTNERS block."""

    id: str
    name: str
    logo: str | None
    website: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalGalleryImageView:
    """One image in a landing GALLERY block."""

    id: str
    url: str
    caption: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalFaqItemView:
    """One question/answer pair in a landing FAQ block."""

    id: str
    question: str
    answer: str


@dataclass(frozen=True, slots=True)
class PublicFestivalLandingBlockView:
    """One enabled landing block, in display order, with its typed payload.

    Only the fields relevant to the block ``type`` are populated; the rest stay
    empty/``None``. ``enabled`` is intentionally absent — disabled blocks are
    dropped by the projection, so every block that reaches the frontend renders.
    """

    id: str
    type: str
    sort_order: int
    title: str | None
    subtitle: str | None
    cover_image: str | None
    body: str | None
    content_format: str | None
    jury: tuple[PublicFestivalJuryCardView, ...] = ()
    partners: tuple[PublicFestivalPartnerCardView, ...] = ()
    images: tuple[PublicFestivalGalleryImageView, ...] = ()
    faq: tuple[PublicFestivalFaqItemView, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicFestivalLandingView:
    """The public landing page: enabled blocks in display order."""

    blocks: tuple[PublicFestivalLandingBlockView, ...] = ()


class _SortableChild(Protocol):
    """Structural type for a landing block's ordered children (jury/partners/…).

    Read-only properties so the frozen-dataclass children satisfy it (mutable
    attribute annotations would be invariant and reject them).
    """

    @property
    def id(self) -> str: ...

    @property
    def sort_order(self) -> int: ...


def _sorted_children[T: _SortableChild](items: tuple[T, ...]) -> list[T]:
    return sorted(items, key=lambda item: (item.sort_order, item.id))


def _project_block(block: LandingBlock) -> PublicFestivalLandingBlockView:
    return PublicFestivalLandingBlockView(
        id=block.id,
        type=block.type.value,
        sort_order=block.sort_order,
        title=block.title,
        subtitle=block.subtitle,
        cover_image=block.cover_image,
        body=block.body,
        content_format=block.content_format,
        jury=tuple(
            PublicFestivalJuryCardView(
                id=card.id,
                name=card.name,
                photo=card.photo,
                position=card.position,
                description=card.description,
            )
            for card in _sorted_children(block.cards)
        ),
        partners=tuple(
            PublicFestivalPartnerCardView(
                id=card.id,
                name=card.name,
                logo=card.logo,
                website=card.website,
            )
            for card in _sorted_children(block.partners)
        ),
        images=tuple(
            PublicFestivalGalleryImageView(id=image.id, url=image.url, caption=image.caption)
            for image in _sorted_children(block.images)
        ),
        faq=tuple(
            PublicFestivalFaqItemView(id=item.id, question=item.question, answer=item.answer)
            for item in _sorted_children(block.faq_items)
        ),
    )


def project_landing(config: LandingConfiguration) -> PublicFestivalLandingView:
    """Project a competition's landing configuration for public display.

    Keeps only enabled blocks, ordered by the organizer's sort order, each with
    its child collections sorted the same way. The HERO block is included (the
    frontend renders it as the page hero); the VENUE block is included as a
    positional marker only — its content is the shared venue/contacts data.
    """
    enabled = tuple(block for block in config.sorted_blocks() if block.enabled)
    return PublicFestivalLandingView(blocks=tuple(_project_block(block) for block in enabled))


# --- Contacts projection ------------------------------------------------------
#
# The public footer/venue reuse the Competition Contacts module verbatim — the
# organizer configures it once and it is the single source of truth. Organization
# profile reuse (``use_organization_contacts``) resolves the organizer *name*
# through the Organization directory (the only cross-context contact fact
# published today); the remaining reach-out channels (phone/email/website/social)
# come from the competition's own contact override, since the Organization
# aggregate does not yet model them (the same documented gap as the organizer
# ``logo``). Venue merges the competition's own venue columns with the contacts
# venue detail (city/country/maps/directions).


@dataclass(frozen=True, slots=True)
class PublicFestivalSocialLinksView:
    """Public social links for the footer."""

    vk: str | None
    instagram: str | None
    telegram: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalTeamMemberView:
    """A named contact person shown on the public page."""

    id: str
    name: str
    position: str | None
    phone: str | None
    email: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalEmergencyView:
    """Optional emergency/urgent contact line."""

    phone: str | None
    email: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class PublicFestivalVenueView:
    """The venue section — competition venue columns merged with contact details."""

    name: str | None
    address: str | None
    city: str | None
    country: str | None
    google_maps_url: str | None
    yandex_maps_url: str | None
    directions: str | None

    @property
    def has_content(self) -> bool:
        return any(
            (
                self.name,
                self.address,
                self.city,
                self.country,
                self.google_maps_url,
                self.yandex_maps_url,
                self.directions,
            )
        )


@dataclass(frozen=True, slots=True)
class PublicFestivalContactsView:
    """The public contacts module: organizer identity, channels, team, venue."""

    organization_name: str | None
    phone: str | None
    email: str | None
    website: str | None
    address: str | None
    social: PublicFestivalSocialLinksView
    team: tuple[PublicFestivalTeamMemberView, ...]
    emergency: PublicFestivalEmergencyView
    venue: PublicFestivalVenueView


def project_contacts(
    config: ContactsConfiguration,
    *,
    organizer_name: str,
    venue_name: str | None,
    venue_address: str | None,
) -> PublicFestivalContactsView:
    """Project a competition's contacts configuration for public display.

    ``organization_name`` prefers the organizer's explicit override, falling back
    to the resolved organizer directory name; the remaining channels come from the
    override. Team members are sorted by the organizer's order. Venue merges the
    competition's own venue columns with the contacts venue detail.
    """
    override = config.override
    team = sorted(config.team_contacts, key=lambda member: (member.sort_order, member.name))
    return PublicFestivalContactsView(
        organization_name=override.organization_name or organizer_name,
        phone=override.phone,
        email=override.email,
        website=override.website,
        address=override.address,
        social=PublicFestivalSocialLinksView(
            vk=override.vk,
            instagram=override.instagram,
            telegram=override.telegram,
        ),
        team=tuple(
            PublicFestivalTeamMemberView(
                id=member.id,
                name=member.name,
                position=member.position,
                phone=member.phone,
                email=member.email,
                description=member.description,
            )
            for member in team
        ),
        emergency=PublicFestivalEmergencyView(
            phone=config.emergency.phone,
            email=config.emergency.email,
            notes=config.emergency.notes,
        ),
        venue=PublicFestivalVenueView(
            name=venue_name,
            address=venue_address,
            city=config.venue_details.city,
            country=config.venue_details.country,
            google_maps_url=config.venue_details.google_maps_url,
            yandex_maps_url=config.venue_details.yandex_maps_url,
            directions=config.venue_details.directions,
        ),
    )


# --- Regulation ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicFestivalRegulationView:
    """The competition's current regulation ("Положение фестиваля").

    The single official rules document a visitor should read before applying.
    Only the *current* version is exposed publicly — superseded versions stay
    private. ``file_reference`` is an opaque storage reference the frontend
    resolves to a downloadable URL.
    """

    title: str
    version: str
    publication_date: date
    file_reference: str


# --- Detail view DTO ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicFestivalDetailView:
    """A single competition's full public landing view.

    Carries everything the catalog card view does (the hero/summary facts) plus
    the rendered landing blocks and the resolved contacts module. It is a
    superset so the frontend can reuse the same formatting for the shared facts.
    """

    id: str
    title: str
    season: str
    description: str | None
    status: str
    organizer: PublicFestivalOrganizerView
    city: str | None
    venue_name: str | None
    venue_address: str | None
    cover_image: str | None
    competition_start: date | None
    competition_end: date | None
    registration_start: date | None
    registration_end: date | None
    application_deadline: datetime | None
    pricing: PublicFestivalPricingView
    formats: tuple[PublicFestivalFormatView, ...]
    modes: tuple[str, ...]
    categories: tuple[str, ...]
    landing: PublicFestivalLandingView
    contacts: PublicFestivalContactsView
    regulation: PublicFestivalRegulationView | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Read-service port --------------------------------------------------------


@runtime_checkable
class PublicCatalogReadService(Protocol):
    """Port: read the public catalog and individual public competitions.

    The presentation edge depends on this port; the composition root wires it to
    the concrete ORM-backed reader. Filtering/sorting/search beyond "public and
    newest-first" is performed client-side by the SPA (live filtering), so the
    list stays a single, cacheable read.
    """

    def list_festivals(self) -> list[PublicFestivalView]:
        """Return every publicly-visible competition, newest first."""
        ...

    def get_festival(self, festival_id: str) -> PublicFestivalDetailView | None:
        """Return one publicly-visible competition's full landing view.

        ``None`` when no competition matches the id *or* it is not in a publicly
        visible lifecycle state — the edge renders a 404 either way, never leaking
        the existence of a draft/archived competition.
        """
        ...
