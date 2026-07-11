import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import type { PublicationChecklist } from "./publication-checklist";
import { COMPETITION_SECTIONS, type CompetitionSectionId } from "./sections";

export interface CompetitionReadinessItem {
  sectionId: CompetitionSectionId;
  label: string;
  done: boolean;
  blocking: boolean;
}

export interface CompetitionReadiness {
  items: CompetitionReadinessItem[];
  percent: number;
  incomplete: number;
}

const BLOCKING_SECTIONS = new Set<CompetitionSectionId>([
  "categories",
  "age-categories",
  "participant-groups",
  "participation-formats",
  "admission-rules",
  "pricing",
  "regulations",
]);

/**
 * Section-level readiness for organizers — complements the detailed publication checklist.
 */
export function buildCompetitionReadiness(
  competition: CompetitionDetail,
  checklist: PublicationChecklist,
): CompetitionReadiness {
  const byId = (id: string): boolean =>
    checklist.items.find((item) => item.id === id)?.done === true;

  function isDone(sectionId: CompetitionSectionId): boolean {
    switch (sectionId) {
      case "general":
        return checklist.generalComplete;
      case "regulations":
        return byId("regulation");
      case "documents":
        return competition.documents.length > 0;
      case "categories":
      case "disciplines":
        return byId("categories") && byId("disciplines");
      case "age-categories":
        return byId("age-categories");
      case "participant-groups":
        return byId("participant-groups");
      case "participation-formats":
        return byId("formats");
      case "admission-rules":
        return byId("admission-rules");
      case "pricing":
        return byId("pricing");
      case "additional-services":
      case "settings":
        return true;
      case "contacts": {
        const config = competition.contactsConfig;
        const hasVenueExtras =
          Boolean(config.venueDetails.city?.trim()) ||
          Boolean(config.venueDetails.country?.trim()) ||
          Boolean(config.venueDetails.googleMapsUrl?.trim()) ||
          Boolean(config.venueDetails.yandexMapsUrl?.trim()) ||
          Boolean(config.venueDetails.directions?.trim());
        return (
          config.teamContacts.length > 0 ||
          hasVenueExtras ||
          Boolean(config.emergency.phone?.trim()) ||
          Boolean(config.emergency.email?.trim()) ||
          Boolean(config.emergency.notes?.trim()) ||
          !config.useOrganizationContacts
        );
      }
      case "public-information":
        return competition.informationBlocks.length > 0;
      default:
        return false;
    }
  }

  const items: CompetitionReadinessItem[] = COMPETITION_SECTIONS.map((section) => ({
    sectionId: section.id,
    label: section.title,
    done: isDone(section.id),
    blocking: BLOCKING_SECTIONS.has(section.id),
  }));

  const doneCount = items.filter((item) => item.done).length;
  const percent = items.length === 0 ? 0 : Math.round((doneCount / items.length) * 100);

  return {
    items,
    percent,
    incomplete: items.filter((item) => !item.done).length,
  };
}
