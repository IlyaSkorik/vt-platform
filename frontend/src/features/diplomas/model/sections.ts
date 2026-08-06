import { Archive, FileStack, LayoutTemplate, type LucideIcon, Sparkles, Type } from "lucide-react";

export type DiplomaSectionId = "templates" | "fonts" | "assignments" | "generation" | "archive";

export interface DiplomaSection {
  id: DiplomaSectionId;
  title: string;
  description: string;
  icon: LucideIcon;
}

export const DIPLOMA_SECTIONS: readonly DiplomaSection[] = [
  {
    id: "templates",
    title: "Шаблоны",
    description: "Библиотека шаблонов дипломов, благодарностей и сертификатов.",
    icon: LayoutTemplate,
  },
  {
    id: "fonts",
    title: "Шрифты",
    description: "Чем набираются дипломы: встроенные семьи и свои загруженные .ttf.",
    icon: Type,
  },
  {
    id: "assignments",
    title: "Назначение",
    description: "Какой шаблон применяется для фестиваля и жанра.",
    icon: FileStack,
  },
  {
    id: "generation",
    title: "Генерация",
    description: "Формирование дипломов и ZIP-архивов по фестивалю.",
    icon: Sparkles,
  },
  {
    id: "archive",
    title: "Архив",
    description: "История генераций и повторное скачивание.",
    icon: Archive,
  },
];

export const DEFAULT_DIPLOMA_SECTION: DiplomaSectionId = "templates";

export function findDiplomaSection(sectionId: string | null | undefined): DiplomaSection {
  const fallback = DIPLOMA_SECTIONS[0];
  if (fallback == null) {
    throw new Error("Diploma sections are not configured.");
  }
  return DIPLOMA_SECTIONS.find((section) => section.id === sectionId) ?? fallback;
}
