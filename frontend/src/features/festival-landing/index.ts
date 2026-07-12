/**
 * Public API of the `festival-landing` feature.
 *
 * Data access (TanStack Query over the public read model's detail endpoint) and
 * framework-free presentation logic (status → CTA mapping, block ordering, price
 * formatting) for the public Competition Landing Page. Widgets compose these;
 * nothing reaches past this barrel. Shared festival formatters (dates, media,
 * modes) are reused from `@/features/festival-catalog`.
 */
export { festivalLandingKeys, usePublicFestival } from "./api";
export {
  bodyBlocks,
  type FaqItem,
  type FestivalContacts,
  type FestivalDetail,
  type FestivalDocument,
  type FestivalVenue,
  formatFromPrice,
  type GalleryImage,
  heroBlock,
  isPublicStatus,
  type JuryCard,
  LANDING_BLOCK_TYPES,
  type LandingBlock,
  type LandingBlockType,
  type LandingCta,
  landingCta,
  type PartnerCard,
  type PublicStatus,
  type Regulation,
  type TeamMember,
} from "./lib";
