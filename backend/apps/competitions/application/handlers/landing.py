"""Use cases: competition public-landing configuration."""

from __future__ import annotations

from apps.competitions.application.dto.commands import UpdateLandingConfigCommand
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.landing_configuration import (
    FaqItem,
    GalleryImage,
    JuryCard,
    LandingBlock,
    LandingBlockType,
    LandingConfiguration,
    PartnerCard,
)

from ._support import CompetitionCommandHandler

__all__ = ("UpdateLandingConfigHandler",)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sort_order(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _landing_config_from_command(command: UpdateLandingConfigCommand) -> LandingConfiguration:
    blocks: list[LandingBlock] = []
    for raw in command.blocks:
        block_type = LandingBlockType(str(raw["type"]))
        cards_raw = raw.get("cards", [])
        partners_raw = raw.get("partners", [])
        images_raw = raw.get("images", [])
        faq_raw = raw.get("faq_items", [])

        cards: list[JuryCard] = []
        if isinstance(cards_raw, list):
            for card in cards_raw:
                if not isinstance(card, dict):
                    continue
                cards.append(
                    JuryCard(
                        id=str(card["id"]),
                        name=str(card["name"]),
                        photo=_optional_str(card.get("photo")),
                        position=_optional_str(card.get("position")),
                        description=_optional_str(card.get("description")),
                        sort_order=_sort_order(card.get("sort_order", 0)),
                    )
                )

        partners: list[PartnerCard] = []
        if isinstance(partners_raw, list):
            for card in partners_raw:
                if not isinstance(card, dict):
                    continue
                partners.append(
                    PartnerCard(
                        id=str(card["id"]),
                        name=str(card["name"]),
                        logo=_optional_str(card.get("logo")),
                        website=_optional_str(card.get("website")),
                        sort_order=_sort_order(card.get("sort_order", 0)),
                    )
                )

        images: list[GalleryImage] = []
        if isinstance(images_raw, list):
            for image in images_raw:
                if not isinstance(image, dict):
                    continue
                images.append(
                    GalleryImage(
                        id=str(image["id"]),
                        url=str(image["url"]),
                        caption=_optional_str(image.get("caption")),
                        sort_order=_sort_order(image.get("sort_order", 0)),
                    )
                )

        faq_items: list[FaqItem] = []
        if isinstance(faq_raw, list):
            for item in faq_raw:
                if not isinstance(item, dict):
                    continue
                faq_items.append(
                    FaqItem(
                        id=str(item["id"]),
                        question=str(item["question"]),
                        answer=str(item["answer"]),
                        sort_order=_sort_order(item.get("sort_order", 0)),
                    )
                )

        body = raw.get("body")
        body_value: str | None = (
            ("" if body is None else str(body))
            if block_type is LandingBlockType.CONTENT
            else _optional_str(body)
        )

        blocks.append(
            LandingBlock(
                id=str(raw["id"]),
                type=block_type,
                enabled=bool(raw.get("enabled", True)),
                sort_order=_sort_order(raw.get("sort_order", 0)),
                title=_optional_str(raw.get("title")),
                subtitle=_optional_str(raw.get("subtitle")),
                cover_image=_optional_str(raw.get("cover_image")),
                body=body_value,
                content_format=_optional_str(raw.get("content_format")),
                cards=tuple(cards),
                partners=tuple(partners),
                images=tuple(images),
                faq_items=tuple(faq_items),
            )
        )

    return LandingConfiguration(blocks=tuple(blocks))


class UpdateLandingConfigHandler(CompetitionCommandHandler):
    """Replace competition public-landing configuration."""

    def handle(self, command: UpdateLandingConfigCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.update_landing_config(
            config=_landing_config_from_command(command),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)
