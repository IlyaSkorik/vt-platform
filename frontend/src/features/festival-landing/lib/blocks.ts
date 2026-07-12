import { LANDING_BLOCK_TYPES, type LandingBlock } from "./types";

/**
 * Order blocks the way the organizer configured them.
 *
 * The backend already returns enabled blocks in `sortOrder` order, but sorting
 * defensively here keeps the ordering guarantee local to the renderer and makes
 * it unit-testable without a server.
 */
function ordered(blocks: LandingBlock[]): LandingBlock[] {
  return [...blocks].sort((a, b) => a.sortOrder - b.sortOrder);
}

/** The single HERO block (the page hero), or `null` if the organizer disabled it. */
export function heroBlock(blocks: LandingBlock[]): LandingBlock | null {
  return blocks.find((block) => block.type === LANDING_BLOCK_TYPES.HERO) ?? null;
}

/**
 * The main-content blocks, in display order — everything except the HERO, which
 * the page renders as its header rather than as a body section.
 */
export function bodyBlocks(blocks: LandingBlock[]): LandingBlock[] {
  return ordered(blocks).filter((block) => block.type !== LANDING_BLOCK_TYPES.HERO);
}
