/**
 * The sections of the jury workspace.
 *
 * Five. "Протоколы" stays first and stays the default: it is the one section every
 * festival uses, online judging or not, and an organizer who has always landed here
 * should keep landing here.
 *
 * The rest follow the order of a festival day — who judges, what they judge, the day
 * itself, the numbers it produced.
 *
 * Three of them are only meaningful when the festival judges online — a festival on
 * protocols has no panel to seat and no act to open — but they are listed regardless.
 * Hiding them would leave an organizer who has just switched the mode on with no way to
 * find what they switched on; each one says what is missing when it is opened.
 */
import {
  FileSpreadsheet,
  Gavel,
  ListChecks,
  type LucideIcon,
  UserCheck,
  Users,
} from "lucide-react";

export type JurySectionId = "protocols" | "members" | "assignments" | "live" | "tally";

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
    description: "Кто судит фестиваль: приглашения, регалии, председатель.",
    icon: Users,
    implemented: true,
  },
  {
    id: "assignments",
    title: "Назначения",
    description: "Кто какие жанры судит. Пусто — значит весь фестиваль.",
    icon: UserCheck,
    implemented: true,
  },
  {
    id: "live",
    title: "Ход судейства",
    description: "Что сейчас на сцене: ведущий открывает и закрывает выступления.",
    icon: Gavel,
    implemented: true,
  },
  {
    id: "tally",
    title: "Итоги",
    description: "Баллы, награды по шкале и перенос результатов в протоколы.",
    icon: ListChecks,
    implemented: true,
  },
];

export const DEFAULT_JURY_SECTION: JurySectionId = "protocols";

export function findJurySection(sectionId: string | null | undefined): JurySection {
  const fallback = JURY_SECTIONS[0];
  if (fallback == null) {
    throw new Error("Разделы жюри не настроены.");
  }
  return JURY_SECTIONS.find((section) => section.id === sectionId) ?? fallback;
}
