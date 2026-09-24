import {
  BookOpen,
  CalendarClock,
  CircleDollarSign,
  ClipboardCheck,
  FileText,
  FolderTree,
  Gavel,
  Globe,
  type LucideIcon,
  Phone,
  Settings,
  ShieldCheck,
  Sparkles,
  Tags,
  Users,
} from "lucide-react";

export type CompetitionSectionId =
  | "general"
  | "regulations"
  | "documents"
  | "categories"
  | "disciplines"
  | "registration"
  | "age-categories"
  | "participant-groups"
  | "participation-formats"
  | "admission-rules"
  | "pricing"
  | "additional-services"
  | "settings"
  | "judging"
  | "contacts"
  | "public-information";

export interface CompetitionSection {
  id: CompetitionSectionId;
  title: string;
  icon: LucideIcon;
  implemented: boolean;
}

/**
 * The sidebar's groups, in order.
 *
 * A flat list of fifteen sections gave no clue which ones belong together, so they
 * are grouped by the question the organizer is answering: what the festival *is*,
 * what it is *divided into*, what an applicant *does*, how it is *decided*, and what
 * it *costs*. Each section appears in exactly one group, and the group order is the
 * rough order a festival gets set up in — describe it, structure it, open it, judge
 * it, price it.
 */
export interface CompetitionSectionGroup {
  title: string;
  sectionIds: readonly CompetitionSectionId[];
}

export const COMPETITION_SECTION_GROUPS: readonly CompetitionSectionGroup[] = [
  {
    title: "Основное",
    sectionIds: ["general", "regulations", "public-information", "contacts"],
  },
  {
    title: "Структура",
    sectionIds: [
      "categories",
      "participant-groups",
      "age-categories",
      "participation-formats",
      "admission-rules",
    ],
  },
  {
    title: "Участие",
    sectionIds: ["registration", "settings", "documents"],
  },
  {
    title: "Итоги",
    sectionIds: ["judging"],
  },
  {
    title: "Деньги",
    sectionIds: ["pricing", "additional-services"],
  },
];

export const COMPETITION_SECTIONS: readonly CompetitionSection[] = [
  { id: "general", title: "Общее", icon: Sparkles, implemented: true },
  { id: "regulations", title: "Положение", icon: BookOpen, implemented: true },
  { id: "public-information", title: "Публичная информация", icon: Globe, implemented: true },
  { id: "contacts", title: "Контакты", icon: Phone, implemented: true },
  { id: "categories", title: "Жанры и номинации", icon: FolderTree, implemented: true },
  { id: "participant-groups", title: "Группы участников", icon: Users, implemented: true },
  { id: "age-categories", title: "Возрастные категории", icon: Tags, implemented: true },
  {
    id: "participation-formats",
    title: "Форматы участия",
    icon: ClipboardCheck,
    implemented: true,
  },
  { id: "admission-rules", title: "Правила допуска", icon: ShieldCheck, implemented: true },
  { id: "registration", title: "Регистрация", icon: CalendarClock, implemented: true },
  { id: "settings", title: "Правила участия", icon: Settings, implemented: true },
  { id: "documents", title: "Документы", icon: FileText, implemented: true },
  // Always listed, whichever judging mode the festival is on: the award scale is the
  // vocabulary protocols are written in, and an organizer who hands out places rather
  // than степени needs it whether or not their jury scores here. What the online mode
  // adds is the rest of the section — criteria, tally rules, the hall's board.
  { id: "judging", title: "Судейство", icon: Gavel, implemented: true },
  { id: "pricing", title: "Цены", icon: CircleDollarSign, implemented: true },
  {
    id: "additional-services",
    title: "Доп. услуги",
    icon: Sparkles,
    implemented: true,
  },
];

/** The sections of one group, resolved and in the group's declared order. */
export function competitionSectionsOfGroup(
  group: CompetitionSectionGroup,
): readonly CompetitionSection[] {
  return group.sectionIds.flatMap(
    (id) => COMPETITION_SECTIONS.find((section) => section.id === id) ?? [],
  );
}

export const DEFAULT_COMPETITION_SECTION: CompetitionSectionId = "general";

/** Legacy `disciplines` URLs resolve to the combined taxonomy section. */
function normalizeSectionId(sectionId: string | null | undefined): string | null | undefined {
  if (sectionId === "disciplines") {
    return "categories";
  }
  return sectionId;
}

export function findCompetitionSection(sectionId: string | null | undefined): CompetitionSection {
  const fallback = COMPETITION_SECTIONS[0];
  if (fallback == null) {
    throw new Error("Разделы фестиваля не настроены.");
  }
  const normalized = normalizeSectionId(sectionId);
  return COMPETITION_SECTIONS.find((section) => section.id === normalized) ?? fallback;
}
