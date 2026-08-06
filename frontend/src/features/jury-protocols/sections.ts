/**
 * The sections of the jury workspace.
 *
 * Only "Протоколы" is implemented, and that is the whole point of the tab today: there is no
 * online scoring, so the jury's work on this platform is entering results per nomination and
 * publishing them. The other two are declared here because the sidebar is where an organizer
 * looks to find out what the tab will grow into, and a listed-but-unimplemented section says
 * that honestly where an absent one would just look like a missing feature.
 */
import { FileSpreadsheet, type LucideIcon, UserCheck, Users } from "lucide-react";

export type JurySectionId = "protocols" | "members" | "assignments";

export interface JurySection {
  id: JurySectionId;
  title: string;
  description: string;
  icon: LucideIcon;
  implemented: boolean;
}

export const JURY_SECTIONS: readonly JurySection[] = [
  {
    id: "protocols",
    title: "Протоколы",
    description: "Результаты по жанрам в порядке выступления, и их публикация.",
    icon: FileSpreadsheet,
    implemented: true,
  },
  {
    id: "members",
    title: "Состав жюри",
    description: "Кто судит фестиваль и в каких жанрах.",
    icon: Users,
    implemented: false,
  },
  {
    id: "assignments",
    title: "Назначения",
    description: "Распределение членов жюри по номинациям и дням.",
    icon: UserCheck,
    implemented: false,
  },
];

export const DEFAULT_JURY_SECTION: JurySectionId = "protocols";

export function findJurySection(sectionId: string | null | undefined): JurySection {
  const fallback = JURY_SECTIONS[0];
  if (fallback == null) {
    throw new Error("Jury sections are not configured.");
  }
  return JURY_SECTIONS.find((section) => section.id === sectionId) ?? fallback;
}
