import type {
  _FaqItem,
  _GalleryImage,
  _JuryCard,
  _LandingBlock,
  _LandingConfig,
  _PartnerCard,
  CompetitionDetail,
  UpdateLandingConfiguration,
} from "@/shared/api/generated/model-competitions";

export const SYSTEM_BLOCK_IDS = {
  HERO: "01900000-0000-7000-8000-000000000001",
  VENUE: "01900000-0000-7000-8000-000000000002",
  JURY: "01900000-0000-7000-8000-000000000003",
  PARTNERS: "01900000-0000-7000-8000-000000000004",
  GALLERY: "01900000-0000-7000-8000-000000000005",
  FAQ: "01900000-0000-7000-8000-000000000006",
} as const;

export type LandingBlockType = _LandingBlock["type"];

export const LANDING_BLOCK_TYPE_LABELS: Record<LandingBlockType, string> = {
  HERO: "Hero",
  VENUE: "Площадка",
  JURY: "Жюри",
  PARTNERS: "Партнёры",
  GALLERY: "Галерея",
  FAQ: "FAQ",
  CONTENT: "Контент",
};

export function defaultLandingConfig(): _LandingConfig {
  return {
    blocks: [
      emptyBlock(SYSTEM_BLOCK_IDS.HERO, "HERO", 0, true),
      emptyBlock(SYSTEM_BLOCK_IDS.VENUE, "VENUE", 1, true),
      emptyBlock(SYSTEM_BLOCK_IDS.JURY, "JURY", 2, false),
      emptyBlock(SYSTEM_BLOCK_IDS.PARTNERS, "PARTNERS", 3, false),
      emptyBlock(SYSTEM_BLOCK_IDS.GALLERY, "GALLERY", 4, false),
      emptyBlock(SYSTEM_BLOCK_IDS.FAQ, "FAQ", 5, false),
    ],
  };
}

export function emptyBlock(
  id: string,
  type: LandingBlockType,
  sortOrder: number,
  enabled: boolean,
): _LandingBlock {
  return {
    id,
    type,
    enabled,
    sortOrder,
    title: null,
    subtitle: null,
    coverImage: null,
    body: null,
    contentFormat: null,
    cards: [],
    partners: [],
    images: [],
    faqItems: [],
  };
}

export function resolveLandingConfig(competition: CompetitionDetail): _LandingConfig {
  const raw = competition.landingConfig;
  if (raw?.blocks?.length) return { blocks: sortLandingBlocks(raw.blocks) };
  return defaultLandingConfig();
}

export function sortLandingBlocks(blocks: _LandingBlock[]): _LandingBlock[] {
  return [...blocks].sort((a, b) => a.sortOrder - b.sortOrder || a.id.localeCompare(b.id));
}

export function blockDisplayTitle(block: _LandingBlock): string {
  if (block.type === "CONTENT") {
    return block.title?.trim() || "Без названия";
  }
  if (block.type === "HERO" && block.title?.trim()) {
    return block.title.trim();
  }
  return LANDING_BLOCK_TYPE_LABELS[block.type];
}

export function isSystemBlock(block: _LandingBlock): boolean {
  return block.type !== "CONTENT";
}

export function createContentBlock(sortOrder: number): _LandingBlock {
  return {
    ...emptyBlock(crypto.randomUUID(), "CONTENT", sortOrder, true),
    title: "Новый раздел",
    body: "",
    contentFormat: "PLAIN",
  };
}

export function createJuryCard(sortOrder: number): _JuryCard {
  return {
    id: crypto.randomUUID(),
    name: "Новый член жюри",
    photo: null,
    position: null,
    description: null,
    sortOrder,
  };
}

export function createPartnerCard(sortOrder: number): _PartnerCard {
  return {
    id: crypto.randomUUID(),
    name: "Новый партнёр",
    logo: null,
    website: null,
    sortOrder,
  };
}

export function createGalleryImage(sortOrder: number, url: string): _GalleryImage {
  return {
    id: crypto.randomUUID(),
    url,
    caption: null,
    sortOrder,
  };
}

export function createFaqItem(sortOrder: number): _FaqItem {
  return {
    id: crypto.randomUUID(),
    question: "Новый вопрос",
    answer: "Ответ",
    sortOrder,
  };
}

export function moveLandingBlockBefore(
  blocks: _LandingBlock[],
  draggedId: string,
  targetId: string,
): _LandingBlock[] {
  if (draggedId === targetId) return blocks;
  const ordered = sortLandingBlocks(blocks);
  const ids = ordered.map((item) => item.id);
  if (!ids.includes(draggedId) || !ids.includes(targetId)) return blocks;
  const without = ids.filter((id) => id !== draggedId);
  const targetIndex = without.indexOf(targetId);
  if (targetIndex < 0) return blocks;
  const nextIds = [...without];
  nextIds.splice(targetIndex, 0, draggedId);
  const byId = new Map(ordered.map((item) => [item.id, item]));
  return nextIds.map((id, index) => {
    const item = byId.get(id);
    if (!item) throw new Error(`Missing block ${id}`);
    return { ...item, sortOrder: index };
  });
}

/** Normalize blocks so domain validation accepts the payload. */
export function sanitizeLandingBlock(block: _LandingBlock): _LandingBlock {
  const base = emptyBlock(block.id, block.type, block.sortOrder, block.enabled);
  switch (block.type) {
    case "HERO":
      return {
        ...base,
        title: blankToNull(block.title),
        subtitle: blankToNull(block.subtitle),
        coverImage: blankToNull(block.coverImage),
      };
    case "VENUE":
      return base;
    case "JURY":
      return {
        ...base,
        cards: (block.cards ?? []).map((card, index) => ({
          ...card,
          name: card.name.trim() || "Без имени",
          photo: blankToNull(card.photo),
          position: blankToNull(card.position),
          description: blankToNull(card.description),
          sortOrder: index,
        })),
      };
    case "PARTNERS":
      return {
        ...base,
        partners: (block.partners ?? []).map((card, index) => ({
          ...card,
          name: card.name.trim() || "Без названия",
          logo: blankToNull(card.logo),
          website: blankToNull(card.website),
          sortOrder: index,
        })),
      };
    case "GALLERY":
      return {
        ...base,
        images: (block.images ?? [])
          .filter((image) => image.url.trim().length > 0)
          .map((image, index) => ({
            ...image,
            url: image.url.trim(),
            caption: blankToNull(image.caption),
            sortOrder: index,
          })),
      };
    case "FAQ":
      return {
        ...base,
        faqItems: (block.faqItems ?? []).map((item, index) => ({
          ...item,
          question: item.question.trim() || "Вопрос",
          answer: item.answer.trim() || "Ответ",
          sortOrder: index,
        })),
      };
    case "CONTENT":
      return {
        ...base,
        title: block.title?.trim() || "Раздел",
        body: block.body ?? "",
        contentFormat: "PLAIN",
      };
    default:
      return base;
  }
}

export function landingConfigToPayload(config: _LandingConfig): UpdateLandingConfiguration {
  return {
    blocks: sortLandingBlocks(config.blocks).map((block, index) =>
      sanitizeLandingBlock({ ...block, sortOrder: index }),
    ),
  };
}

export interface LandingStructureItem {
  id: string;
  label: string;
  enabled: boolean;
  type: LandingBlockType;
}

export function buildLandingStructure(config: _LandingConfig): LandingStructureItem[] {
  return sortLandingBlocks(config.blocks).map((block) => ({
    id: block.id,
    label: blockDisplayTitle(block),
    enabled: block.enabled,
    type: block.type,
  }));
}

function blankToNull(value: string | null | undefined): string | null {
  if (value == null) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}
