"""Public landing-page configuration value objects for a competition.

Drives the Competition Public Landing Builder: ordered blocks (hero, venue,
jury, partners, gallery, FAQ, free-form content) with typed card payloads.
Separate from legacy :class:`~apps.competitions.domain.entities.InformationBlock`
children.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from enum import StrEnum

from .exceptions import InvalidLandingConfigurationError

__all__ = [
    "SYSTEM_BLOCK_DOCUMENTS_ID",
    "SYSTEM_BLOCK_FAQ_ID",
    "SYSTEM_BLOCK_GALLERY_ID",
    "SYSTEM_BLOCK_HERO_ID",
    "SYSTEM_BLOCK_JURY_ID",
    "SYSTEM_BLOCK_PARTNERS_ID",
    "SYSTEM_BLOCK_REGULATION_ID",
    "SYSTEM_BLOCK_VENUE_ID",
    "FaqItem",
    "GalleryImage",
    "JuryCard",
    "LandingBlock",
    "LandingBlockType",
    "LandingConfiguration",
    "PartnerCard",
]

# Well-known UUID v7-looking constants for the system blocks.
SYSTEM_BLOCK_HERO_ID: str = "01900000-0000-7000-8000-000000000001"
SYSTEM_BLOCK_VENUE_ID: str = "01900000-0000-7000-8000-000000000002"
SYSTEM_BLOCK_JURY_ID: str = "01900000-0000-7000-8000-000000000003"
SYSTEM_BLOCK_PARTNERS_ID: str = "01900000-0000-7000-8000-000000000004"
SYSTEM_BLOCK_GALLERY_ID: str = "01900000-0000-7000-8000-000000000005"
SYSTEM_BLOCK_FAQ_ID: str = "01900000-0000-7000-8000-000000000006"
SYSTEM_BLOCK_REGULATION_ID: str = "01900000-0000-7000-8000-000000000007"
SYSTEM_BLOCK_DOCUMENTS_ID: str = "01900000-0000-7000-8000-000000000008"


class LandingBlockType(StrEnum):
    """Block kinds available on the public competition landing page."""

    HERO = "HERO"
    VENUE = "VENUE"
    JURY = "JURY"
    PARTNERS = "PARTNERS"
    GALLERY = "GALLERY"
    FAQ = "FAQ"
    CONTENT = "CONTENT"
    # Positional markers (like VENUE): carry no payload of their own; they mark
    # where the competition's current regulation ("Положение фестиваля") and its
    # public documents are rendered.
    REGULATION = "REGULATION"
    DOCUMENTS = "DOCUMENTS"


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _require_uuid(value: str, *, label: str) -> None:
    try:
        uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidLandingConfigurationError(f"{label} id must be a valid UUID.") from exc


@dataclass(frozen=True, slots=True)
class JuryCard:
    """A jury / expert card shown in the JURY block."""

    id: str
    name: str
    photo: str | None = None
    position: str | None = None
    description: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        _require_uuid(self.id, label="Jury card")
        name = (self.name or "").strip()
        if not name:
            raise InvalidLandingConfigurationError("Укажите имя члена жюри.")
        if self.sort_order < 0:
            raise InvalidLandingConfigurationError("Порядок карточки жюри не может быть отрицательным.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "photo", _optional_str(self.photo))
        object.__setattr__(self, "position", _optional_str(self.position))
        object.__setattr__(self, "description", _optional_str(self.description))


@dataclass(frozen=True, slots=True)
class PartnerCard:
    """A partner / sponsor card shown in the PARTNERS block."""

    id: str
    name: str
    logo: str | None = None
    website: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        _require_uuid(self.id, label="Partner card")
        name = (self.name or "").strip()
        if not name:
            raise InvalidLandingConfigurationError("Укажите название партнёра.")
        if self.sort_order < 0:
            raise InvalidLandingConfigurationError("Порядок карточки партнёра не может быть отрицательным.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "logo", _optional_str(self.logo))
        object.__setattr__(self, "website", _optional_str(self.website))


@dataclass(frozen=True, slots=True)
class GalleryImage:
    """An image entry in the GALLERY block."""

    id: str
    url: str
    caption: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        _require_uuid(self.id, label="Gallery image")
        url = (self.url or "").strip()
        if not url:
            raise InvalidLandingConfigurationError("Укажите ссылку на изображение галереи.")
        if self.sort_order < 0:
            raise InvalidLandingConfigurationError("Порядок изображения галереи не может быть отрицательным.")
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "caption", _optional_str(self.caption))


@dataclass(frozen=True, slots=True)
class FaqItem:
    """A question/answer pair in the FAQ block."""

    id: str
    question: str
    answer: str
    sort_order: int = 0

    def __post_init__(self) -> None:
        _require_uuid(self.id, label="FAQ item")
        question = (self.question or "").strip()
        answer = (self.answer or "").strip()
        if not question:
            raise InvalidLandingConfigurationError("Укажите вопрос.")
        if not answer:
            raise InvalidLandingConfigurationError("Укажите ответ на вопрос.")
        if self.sort_order < 0:
            raise InvalidLandingConfigurationError("Порядок вопроса не может быть отрицательным.")
        object.__setattr__(self, "question", question)
        object.__setattr__(self, "answer", answer)


@dataclass(frozen=True, slots=True)
class LandingBlock:
    """One landing-page block — flat payload; type decides which fields apply."""

    id: str
    type: LandingBlockType
    enabled: bool
    sort_order: int
    title: str | None = None
    subtitle: str | None = None
    cover_image: str | None = None
    body: str | None = None
    content_format: str | None = None
    cards: tuple[JuryCard, ...] = ()
    partners: tuple[PartnerCard, ...] = ()
    images: tuple[GalleryImage, ...] = ()
    faq_items: tuple[FaqItem, ...] = ()

    def __post_init__(self) -> None:
        _require_uuid(self.id, label="Landing block")
        if not isinstance(self.type, LandingBlockType):
            try:
                object.__setattr__(self, "type", LandingBlockType(str(self.type)))
            except ValueError as exc:
                raise InvalidLandingConfigurationError(f"Unknown landing block type: {self.type!r}.") from exc
        if self.sort_order < 0:
            raise InvalidLandingConfigurationError("Порядок блока лендинга не может быть отрицательным.")

        object.__setattr__(self, "title", _optional_str(self.title))
        object.__setattr__(self, "subtitle", _optional_str(self.subtitle))
        object.__setattr__(self, "cover_image", _optional_str(self.cover_image))

        # Blank body / content_format are treated as absent except on CONTENT.
        if self.type is not LandingBlockType.CONTENT:
            if self.body is not None and not str(self.body).strip():
                object.__setattr__(self, "body", None)
            if self.content_format is not None and not str(self.content_format).strip():
                object.__setattr__(self, "content_format", None)
        else:
            object.__setattr__(self, "content_format", _optional_str(self.content_format))

        # Each loop binds its own name: reusing one `item` made the checker infer the
        # first loop's element type for all four and reject the rest as mismatches.
        # The checks themselves stay — these collections are built from a JSON column,
        # so the annotations are a claim to verify at construction, not a guarantee.
        for card in self.cards:
            if not isinstance(card, JuryCard):
                raise InvalidLandingConfigurationError("Jury cards must be JuryCard values.")
        for partner in self.partners:
            if not isinstance(partner, PartnerCard):
                raise InvalidLandingConfigurationError("Partner cards must be PartnerCard values.")
        for image in self.images:
            if not isinstance(image, GalleryImage):
                raise InvalidLandingConfigurationError("Gallery images must be GalleryImage values.")
        for faq_item in self.faq_items:
            if not isinstance(faq_item, FaqItem):
                raise InvalidLandingConfigurationError("FAQ items must be FaqItem values.")

        self._validate_unique_child_ids(self.cards, label="jury card")
        self._validate_unique_child_ids(self.partners, label="partner card")
        self._validate_unique_child_ids(self.images, label="gallery image")
        self._validate_unique_child_ids(self.faq_items, label="FAQ item")

        block_type = self.type
        if block_type in (
            LandingBlockType.VENUE,
            LandingBlockType.REGULATION,
            LandingBlockType.DOCUMENTS,
        ):
            # Positional markers: their content comes from the competition
            # (contacts venue / current regulation / public documents), so they
            # carry no payload.
            self._assert_no_payload(allow_collections=False)
        elif block_type is LandingBlockType.HERO:
            if self.cards or self.partners or self.images or self.faq_items:
                raise InvalidLandingConfigurationError("HERO block must not carry cards, partners, images, or FAQ items.")
            if self.body is not None or self.content_format is not None:
                raise InvalidLandingConfigurationError("HERO block must not carry body or content_format.")
        elif block_type is LandingBlockType.JURY:
            if self.partners or self.images or self.faq_items:
                raise InvalidLandingConfigurationError("JURY block must only use cards.")
            self._assert_no_text_payload()
        elif block_type is LandingBlockType.PARTNERS:
            if self.cards or self.images or self.faq_items:
                raise InvalidLandingConfigurationError("PARTNERS block must only use partners.")
            self._assert_no_text_payload()
        elif block_type is LandingBlockType.GALLERY:
            if self.cards or self.partners or self.faq_items:
                raise InvalidLandingConfigurationError("GALLERY block must only use images.")
            self._assert_no_text_payload()
        elif block_type is LandingBlockType.FAQ:
            if self.cards or self.partners or self.images:
                raise InvalidLandingConfigurationError("FAQ block must only use faq_items.")
            self._assert_no_text_payload()
        elif block_type is LandingBlockType.CONTENT:
            title = self.title
            if not title:
                raise InvalidLandingConfigurationError("У текстового блока должен быть заголовок.")
            if self.cards or self.partners or self.images or self.faq_items:
                raise InvalidLandingConfigurationError("CONTENT block must not carry cards, partners, images, or FAQ items.")
            if self.subtitle is not None or self.cover_image is not None:
                raise InvalidLandingConfigurationError("CONTENT block must not carry subtitle or cover_image.")
            body = self.body if self.body is not None else ""
            fmt = (self.content_format or "PLAIN").strip().upper() or "PLAIN"
            object.__setattr__(self, "body", body)
            object.__setattr__(self, "content_format", fmt)

    @staticmethod
    def _validate_unique_child_ids(items: tuple[object, ...], *, label: str) -> None:
        seen: set[str] = set()
        for item in items:
            item_id = getattr(item, "id", None)
            if not isinstance(item_id, str):
                continue
            if item_id in seen:
                raise InvalidLandingConfigurationError(f"Duplicate {label} id.")
            seen.add(item_id)

    def _assert_no_text_payload(self) -> None:
        if (
            self.title is not None
            or self.subtitle is not None
            or self.cover_image is not None
            or self.body is not None
            or self.content_format is not None
        ):
            raise InvalidLandingConfigurationError(f"{self.type.value} block must not carry title, subtitle, cover_image, body, or content_format.")

    def _assert_no_payload(self, *, allow_collections: bool) -> None:
        self._assert_no_text_payload()
        if not allow_collections and (self.cards or self.partners or self.images or self.faq_items):
            raise InvalidLandingConfigurationError(f"{self.type.value} block must not carry cards, partners, images, or FAQ items.")

    def with_changes(self, **changes: object) -> LandingBlock:
        # Heterogeneous by nature (see CompetitionSettings.with_changes): the checker
        # cannot match each key against its field, and `replace` enforces it at runtime.
        return replace(self, **changes)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class LandingConfiguration:
    """Immutable public-landing configuration for a competition."""

    blocks: tuple[LandingBlock, ...] = ()

    def __post_init__(self) -> None:
        seen_ids: set[str] = set()
        type_counts: dict[LandingBlockType, int] = {}
        for block in self.blocks:
            if not isinstance(block, LandingBlock):
                raise InvalidLandingConfigurationError("Blocks must be LandingBlock values.")
            if block.id in seen_ids:
                raise InvalidLandingConfigurationError("Duplicate landing block id.")
            seen_ids.add(block.id)
            type_counts[block.type] = type_counts.get(block.type, 0) + 1

        if type_counts.get(LandingBlockType.HERO, 0) != 1:
            raise InvalidLandingConfigurationError("На лендинге должен быть ровно один блок-обложка.")
        if type_counts.get(LandingBlockType.VENUE, 0) != 1:
            raise InvalidLandingConfigurationError("На лендинге должен быть ровно один блок с площадкой.")
        for system_type in (
            LandingBlockType.JURY,
            LandingBlockType.PARTNERS,
            LandingBlockType.GALLERY,
            LandingBlockType.FAQ,
            # REGULATION and DOCUMENTS are at-most-one (not required): configs
            # persisted before they existed simply have none, and stay valid.
            LandingBlockType.REGULATION,
            LandingBlockType.DOCUMENTS,
        ):
            if type_counts.get(system_type, 0) > 1:
                raise InvalidLandingConfigurationError(f"Landing configuration allows at most one {system_type.value} block.")

    @classmethod
    def default(cls) -> LandingConfiguration:
        """Seed the system blocks (CONTENT starts empty).

        HERO, REGULATION, DOCUMENTS and VENUE ship enabled (the official facts a
        visitor expects up front); the rest start disabled. The organizer can
        toggle any of them and reorder freely — REGULATION and DOCUMENTS included.
        """
        return cls(
            blocks=(
                LandingBlock(
                    id=SYSTEM_BLOCK_HERO_ID,
                    type=LandingBlockType.HERO,
                    enabled=True,
                    sort_order=0,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_REGULATION_ID,
                    type=LandingBlockType.REGULATION,
                    enabled=True,
                    sort_order=1,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_DOCUMENTS_ID,
                    type=LandingBlockType.DOCUMENTS,
                    enabled=True,
                    sort_order=2,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_VENUE_ID,
                    type=LandingBlockType.VENUE,
                    enabled=True,
                    sort_order=3,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_JURY_ID,
                    type=LandingBlockType.JURY,
                    enabled=False,
                    sort_order=4,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_PARTNERS_ID,
                    type=LandingBlockType.PARTNERS,
                    enabled=False,
                    sort_order=5,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_GALLERY_ID,
                    type=LandingBlockType.GALLERY,
                    enabled=False,
                    sort_order=6,
                ),
                LandingBlock(
                    id=SYSTEM_BLOCK_FAQ_ID,
                    type=LandingBlockType.FAQ,
                    enabled=False,
                    sort_order=7,
                ),
            )
        )

    def with_changes(self, **changes: object) -> LandingConfiguration:
        """A copy with the given fields overridden (rejects unknown names)."""
        return replace(self, **changes)  # type: ignore[arg-type]

    def sorted_blocks(self) -> tuple[LandingBlock, ...]:
        """Blocks ordered by ``sort_order``, then id."""
        return tuple(sorted(self.blocks, key=lambda b: (b.sort_order, b.id)))
