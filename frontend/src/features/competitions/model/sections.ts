import {
  BookOpen,
  CircleDollarSign,
  ClipboardCheck,
  FileText,
  FolderTree,
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
  | "age-categories"
  | "participant-groups"
  | "participation-formats"
  | "admission-rules"
  | "pricing"
  | "additional-services"
  | "settings"
  | "contacts"
  | "public-information";

export interface CompetitionSection {
  id: CompetitionSectionId;
  title: string;
  icon: LucideIcon;
  implemented: boolean;
}

export const COMPETITION_SECTIONS: readonly CompetitionSection[] = [
  { id: "general", title: "Общее", icon: Sparkles, implemented: true },
  { id: "regulations", title: "Положение", icon: BookOpen, implemented: true },
  { id: "documents", title: "Документы", icon: FileText, implemented: true },
  { id: "categories", title: "Номинации и дисциплины", icon: FolderTree, implemented: true },
  { id: "age-categories", title: "Возрастные категории", icon: Tags, implemented: true },
  { id: "participant-groups", title: "Группы участников", icon: Users, implemented: true },
  {
    id: "participation-formats",
    title: "Форматы участия",
    icon: ClipboardCheck,
    implemented: true,
  },
  { id: "admission-rules", title: "Правила допуска", icon: ShieldCheck, implemented: true },
  { id: "pricing", title: "Цены", icon: CircleDollarSign, implemented: true },
  {
    id: "additional-services",
    title: "Доп. услуги",
    icon: Sparkles,
    implemented: true,
  },
  { id: "settings", title: "Правила участия", icon: Settings, implemented: true },
  { id: "contacts", title: "Контакты", icon: Phone, implemented: true },
  { id: "public-information", title: "Публичная информация", icon: Globe, implemented: false },
];

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
    throw new Error("Competition sections are not configured.");
  }
  const normalized = normalizeSectionId(sectionId);
  return COMPETITION_SECTIONS.find((section) => section.id === normalized) ?? fallback;
}
