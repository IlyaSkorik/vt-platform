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

__all__ = [
    "PUBLIC_CATALOG_DOMAIN_STATUSES",
    "ParticipationMode",
    "PublicCatalogReadService",
    "PublicFestivalFormatView",
    "PublicFestivalOrganizerView",
    "PublicFestivalPricingView",
    "PublicFestivalView",
    "aggregate_pricing",
    "classify_participation_mode",
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


# --- Read-service port --------------------------------------------------------


@runtime_checkable
class PublicCatalogReadService(Protocol):
    """Port: return the public catalog, newest first.

    The presentation edge depends on this port; the composition root wires it to
    the concrete ORM-backed reader. Filtering/sorting/search beyond "public and
    newest-first" is performed client-side by the SPA (live filtering), so the
    port stays a single, cacheable read.
    """

    def list_festivals(self) -> list[PublicFestivalView]:
        """Return every publicly-visible competition, newest first."""
        ...
