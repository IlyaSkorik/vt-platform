"""Landing-config JSON ACL helpers for the Competition aggregate.

Translates
:class:`~apps.competitions.domain.landing_configuration.LandingConfiguration`
to/from the root row's ``landing_config`` JSON column.
"""

from __future__ import annotations

from apps.competitions.domain.landing_configuration import (
    FaqItem,
    GalleryImage,
    JuryCard,
    LandingBlock,
    LandingBlockType,
    LandingConfiguration,
    PartnerCard,
)
from shared.utils.json_values import as_int

__all__ = ["landing_config_from_json", "landing_config_to_json"]


def landing_config_to_json(config: LandingConfiguration) -> dict[str, object]:
    """Serialize landing configuration for the competitions.landing_config JSON column."""
    return {
        "blocks": [
            {
                "id": block.id,
                "type": block.type.value,
                "enabled": block.enabled,
                "sort_order": block.sort_order,
                "title": block.title,
                "subtitle": block.subtitle,
                "cover_image": block.cover_image,
                "body": block.body,
                "content_format": block.content_format,
                "cards": [
                    {
                        "id": card.id,
                        "photo": card.photo,
                        "name": card.name,
                        "position": card.position,
                        "description": card.description,
                        "sort_order": card.sort_order,
                    }
                    for card in block.cards
                ],
                "partners": [
                    {
                        "id": card.id,
                        "logo": card.logo,
                        "name": card.name,
                        "website": card.website,
                        "sort_order": card.sort_order,
                    }
                    for card in block.partners
                ],
                "images": [
                    {
                        "id": image.id,
                        "url": image.url,
                        "caption": image.caption,
                        "sort_order": image.sort_order,
                    }
                    for image in block.images
                ],
                "faq_items": [
                    {
                        "id": item.id,
                        "question": item.question,
                        "answer": item.answer,
                        "sort_order": item.sort_order,
                    }
                    for item in block.faq_items
                ],
            }
            for block in config.blocks
        ]
    }


def landing_config_from_json(data: object) -> LandingConfiguration:
    """Rebuild landing configuration from JSON, falling back to defaults."""
    default = LandingConfiguration.default()
    if not isinstance(data, dict) or not data:
        return default

    blocks_raw = data.get("blocks")
    if not isinstance(blocks_raw, list) or not blocks_raw:
        return default

    blocks: list[LandingBlock] = []
    for item in blocks_raw:
        if not isinstance(item, dict):
            continue
        parsed = _block_from_json(item)
        if parsed is not None:
            blocks.append(parsed)

    if not blocks:
        return default

    try:
        return LandingConfiguration(blocks=tuple(blocks))
    except Exception:
        return default


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _sort_order(value: object) -> int:
    return as_int(value, minimum=0)


def _rows(value: object) -> list[dict[str, object]]:
    """The nested JSON arrays-of-objects, narrowed once.

    Bound to a local before the ``isinstance`` check: the previous
    ``data.get(k, []) if isinstance(data.get(k), list) else []`` called ``get`` twice,
    so the check narrowed a different expression than the one whose value was used.
    """
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _block_from_json(data: dict[str, object]) -> LandingBlock | None:
    raw_id = data.get("id")
    raw_type = data.get("type")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    if not isinstance(raw_type, str) or not raw_type:
        return None
    try:
        block_type = LandingBlockType(raw_type)
    except ValueError:
        return None

    cards: list[JuryCard] = []
    for row in _rows(data.get("cards")):
        card = _jury_card_from_json(row)
        if card is not None:
            cards.append(card)

    partners: list[PartnerCard] = []
    for row in _rows(data.get("partners")):
        partner = _partner_card_from_json(row)
        if partner is not None:
            partners.append(partner)

    images: list[GalleryImage] = []
    for row in _rows(data.get("images")):
        image = _gallery_image_from_json(row)
        if image is not None:
            images.append(image)

    faq_items: list[FaqItem] = []
    for row in _rows(data.get("faq_items", data.get("faqItems"))):
        faq_item = _faq_item_from_json(row)
        if faq_item is not None:
            faq_items.append(faq_item)

    try:
        return LandingBlock(
            id=raw_id,
            type=block_type,
            enabled=bool(data.get("enabled", True)),
            sort_order=_sort_order(data.get("sort_order", data.get("sortOrder", 0))),
            title=_str_or_none(data.get("title")),
            subtitle=_str_or_none(data.get("subtitle")),
            cover_image=_str_or_none(data.get("cover_image", data.get("coverImage"))),
            body=_str_or_none(data.get("body")),
            content_format=_str_or_none(data.get("content_format", data.get("contentFormat"))),
            cards=tuple(cards),
            partners=tuple(partners),
            images=tuple(images),
            faq_items=tuple(faq_items),
        )
    except Exception:
        return None


def _jury_card_from_json(data: dict[str, object]) -> JuryCard | None:
    raw_id = data.get("id")
    raw_name = data.get("name")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None
    try:
        return JuryCard(
            id=raw_id,
            name=raw_name,
            photo=_str_or_none(data.get("photo")),
            position=_str_or_none(data.get("position")),
            description=_str_or_none(data.get("description")),
            sort_order=_sort_order(data.get("sort_order", data.get("sortOrder", 0))),
        )
    except Exception:
        return None


def _partner_card_from_json(data: dict[str, object]) -> PartnerCard | None:
    raw_id = data.get("id")
    raw_name = data.get("name")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None
    try:
        return PartnerCard(
            id=raw_id,
            name=raw_name,
            logo=_str_or_none(data.get("logo")),
            website=_str_or_none(data.get("website")),
            sort_order=_sort_order(data.get("sort_order", data.get("sortOrder", 0))),
        )
    except Exception:
        return None


def _gallery_image_from_json(data: dict[str, object]) -> GalleryImage | None:
    raw_id = data.get("id")
    raw_url = data.get("url")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    try:
        return GalleryImage(
            id=raw_id,
            url=raw_url,
            caption=_str_or_none(data.get("caption")),
            sort_order=_sort_order(data.get("sort_order", data.get("sortOrder", 0))),
        )
    except Exception:
        return None


def _faq_item_from_json(data: dict[str, object]) -> FaqItem | None:
    raw_id = data.get("id")
    raw_question = data.get("question")
    raw_answer = data.get("answer")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    if not isinstance(raw_question, str) or not raw_question.strip():
        return None
    if not isinstance(raw_answer, str) or not raw_answer.strip():
        return None
    try:
        return FaqItem(
            id=raw_id,
            question=raw_question,
            answer=raw_answer,
            sort_order=_sort_order(data.get("sort_order", data.get("sortOrder", 0))),
        )
    except Exception:
        return None
