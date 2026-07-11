import {
  BookOpen,
  CircleDollarSign,
  ClipboardCheck,
  FileText,
  FolderTree,
  Globe,
  Layers,
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
  { id: "documents", title: "Документы", icon: FileText, implemented: false },
  { id: "categories", title: "Категории", icon: FolderTree, implemented: false },
  { id: "disciplines", title: "Дисциплины", icon: Layers, implemented: false },
  { id: "age-categories", title: "Возрастные категории", icon: Tags, implemented: false },
  { id: "participant-groups", title: "Группы участников", icon: Users, implemented: false },
  {
    id: "participation-formats",
    title: "Форматы участия",
    icon: ClipboardCheck,
    implemented: false,
  },
  { id: "admission-rules", title: "Правила допуска", icon: ShieldCheck, implemented: false },
  { id: "pricing", title: "Цены", icon: CircleDollarSign, implemented: false },
  {
    id: "additional-services",
    title: "Доп. услуги",
    icon: Sparkles,
    implemented: false,
  },
  { id: "settings", title: "Настройки", icon: Settings, implemented: false },
  { id: "contacts", title: "Контакты", icon: Phone, implemented: false },
  { id: "public-information", title: "Публичная информация", icon: Globe, implemented: false },
];

export const DEFAULT_COMPETITION_SECTION: CompetitionSectionId = "general";

export function findCompetitionSection(sectionId: string | null | undefined): CompetitionSection {
  const fallback = COMPETITION_SECTIONS[0];
  if (fallback == null) {
    throw new Error("Competition sections are not configured.");
  }
  return COMPETITION_SECTIONS.find((section) => section.id === sectionId) ?? fallback;
}
