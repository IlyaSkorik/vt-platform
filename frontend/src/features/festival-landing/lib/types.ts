import type {
  PublicFestivalContacts,
  PublicFestivalDetail,
  PublicFestivalFaqItem,
  PublicFestivalGalleryImage,
  PublicFestivalJuryCard,
  PublicFestivalLandingBlock,
  PublicFestivalPartnerCard,
  PublicFestivalRegulation,
  PublicFestivalTeamMember,
  PublicFestivalVenue,
} from "@/shared/api/generated/model-public-catalog";

/**
 * Domain types for the public Competition Landing Page.
 *
 * The Orval-generated wire models are used directly as the working view models —
 * the landing page is read-only, so there is no reason to remap. These aliases
 * give the feature an intention-revealing vocabulary and a single place to evolve
 * the shape if the projection and the UI ever diverge.
 */
export type FestivalDetail = PublicFestivalDetail;
export type LandingBlock = PublicFestivalLandingBlock;
export type FestivalContacts = PublicFestivalContacts;
export type FestivalVenue = PublicFestivalVenue;
export type JuryCard = PublicFestivalJuryCard;
export type PartnerCard = PublicFestivalPartnerCard;
export type GalleryImage = PublicFestivalGalleryImage;
export type FaqItem = PublicFestivalFaqItem;
export type TeamMember = PublicFestivalTeamMember;
export type Regulation = PublicFestivalRegulation;

/** Public lifecycle status projected by the backend read model. */
export type PublicStatus =
  | "COMING_SOON"
  | "REGISTRATION_OPEN"
  | "REGISTRATION_CLOSED"
  | "RUNNING"
  | "COMPLETED";

/** The block kinds the Landing Builder can render, mirroring the domain enum. */
export const LANDING_BLOCK_TYPES = {
  HERO: "HERO",
  VENUE: "VENUE",
  JURY: "JURY",
  PARTNERS: "PARTNERS",
  GALLERY: "GALLERY",
  FAQ: "FAQ",
  CONTENT: "CONTENT",
  REGULATION: "REGULATION",
} as const;

export type LandingBlockType = (typeof LANDING_BLOCK_TYPES)[keyof typeof LANDING_BLOCK_TYPES];
