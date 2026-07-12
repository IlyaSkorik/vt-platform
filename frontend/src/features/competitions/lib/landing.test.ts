import { describe, expect, it } from "vitest";
import {
  blockDisplayTitle,
  createContentBlock,
  createFaqItem,
  createGalleryImage,
  createJuryCard,
  createPartnerCard,
  defaultLandingConfig,
  landingConfigToPayload,
  moveLandingBlockBefore,
  sanitizeLandingBlock,
} from "./landing";

describe("landing helpers", () => {
  it("seeds the system blocks by default", () => {
    const config = defaultLandingConfig();
    expect(config.blocks).toHaveLength(8);
    expect(config.blocks.map((block) => block.type)).toEqual([
      "HERO",
      "REGULATION",
      "DOCUMENTS",
      "VENUE",
      "JURY",
      "PARTNERS",
      "GALLERY",
      "FAQ",
    ]);
  });

  it("sanitizes hero blocks without body fields", () => {
    const hero = defaultLandingConfig().blocks[0];
    if (!hero) throw new Error("missing hero");
    const sanitized = sanitizeLandingBlock({
      ...hero,
      title: "  Festival  ",
      body: "should drop",
      contentFormat: "PLAIN",
    });
    expect(sanitized.title).toBe("Festival");
    expect(sanitized.body).toBeNull();
    expect(sanitized.contentFormat).toBeNull();
  });

  it("moves blocks before a target", () => {
    const blocks = defaultLandingConfig().blocks;
    const hero = blocks[0];
    const faq = blocks[5];
    if (!hero || !faq) throw new Error("missing blocks");
    const next = moveLandingBlockBefore(blocks, hero.id, faq.id);
    expect(next.map((block) => block.type)[0]).toBe("REGULATION");
    expect(next.find((block) => block.id === hero.id)?.sortOrder).toBeLessThan(
      next.find((block) => block.id === faq.id)?.sortOrder ?? 99,
    );
  });

  it("creates content blocks with required title/body", () => {
    const block = createContentBlock(6);
    expect(block.type).toBe("CONTENT");
    const payload = landingConfigToPayload({
      blocks: [...defaultLandingConfig().blocks, block],
    });
    const content = payload.blocks.find((item) => item.type === "CONTENT");
    expect(content?.title).toBeTruthy();
    expect(content?.body).toBe("");
    expect(content?.contentFormat).toBe("PLAIN");
  });

  it("uses custom title for content display", () => {
    expect(blockDisplayTitle(createContentBlock(0))).toBe("Новый раздел");
  });

  it("keeps draft jury and partner cards through sanitize", () => {
    const jury = defaultLandingConfig().blocks.find((block) => block.type === "JURY");
    if (!jury) throw new Error("missing jury");
    const withCard = {
      ...jury,
      cards: [createJuryCard(0)],
    };
    const sanitized = sanitizeLandingBlock(withCard);
    expect(sanitized.cards).toHaveLength(1);
    expect(sanitized.cards[0]?.name).toBe("Новый член жюри");

    const partners = defaultLandingConfig().blocks.find((block) => block.type === "PARTNERS");
    if (!partners) throw new Error("missing partners");
    const withPartner = {
      ...partners,
      partners: [createPartnerCard(0)],
    };
    expect(sanitizeLandingBlock(withPartner).partners).toHaveLength(1);
  });

  it("keeps faq drafts and gallery images with urls", () => {
    const faq = defaultLandingConfig().blocks.find((block) => block.type === "FAQ");
    if (!faq) throw new Error("missing faq");
    const sanitizedFaq = sanitizeLandingBlock({
      ...faq,
      faqItems: [createFaqItem(0)],
    });
    expect(sanitizedFaq.faqItems).toHaveLength(1);

    const gallery = defaultLandingConfig().blocks.find((block) => block.type === "GALLERY");
    if (!gallery) throw new Error("missing gallery");
    const sanitizedGallery = sanitizeLandingBlock({
      ...gallery,
      images: [createGalleryImage(0, "/media/competitions/x/landing/a.jpg")],
    });
    expect(sanitizedGallery.images).toHaveLength(1);
  });
});
