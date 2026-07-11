import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import type { CompetitionSectionId } from "./sections";

export interface PublicationChecklistItem {
  id: string;
  label: string;
  done: boolean;
  sectionId: CompetitionSectionId;
  blocking: boolean;
}

export interface PublicationChecklist {
  items: PublicationChecklistItem[];
  blockingIncomplete: number;
  isPublishable: boolean;
  generalComplete: boolean;
}

function hasText(value: string | null | undefined): boolean {
  return Boolean(value?.trim());
}

function hasPeriod(
  period: CompetitionDetail["registrationPeriod"] | CompetitionDetail["competitionPeriod"],
): boolean {
  return hasText(period?.start) && hasText(period?.end);
}

/**
 * Client-side publication readiness checklist aligned with the backend
 * `Competition.publication_report()` rules, plus General-section completeness.
 */
export function buildPublicationChecklist(competition: CompetitionDetail): PublicationChecklist {
  const generalItems: PublicationChecklistItem[] = [
    {
      id: "title",
      label: "Название фестиваля",
      done:
        hasText(competition.title) &&
        competition.title.trim() !== "Новый фестиваль" &&
        competition.title.trim() !== "New Competition",
      sectionId: "general",
      blocking: false,
    },
    {
      id: "description",
      label: "Краткое описание",
      done: hasText(competition.description),
      sectionId: "general",
      blocking: false,
    },
    {
      id: "registration-period",
      label: "Даты регистрации",
      done: hasPeriod(competition.registrationPeriod),
      sectionId: "general",
      blocking: false,
    },
    {
      id: "competition-period",
      label: "Даты фестиваля",
      done: hasPeriod(competition.competitionPeriod),
      sectionId: "general",
      blocking: false,
    },
    {
      id: "venue",
      label: "Площадка",
      done: hasText(competition.venue?.name) || hasText(competition.venue?.address),
      sectionId: "general",
      blocking: false,
    },
  ];

  const taxonomyItems: PublicationChecklistItem[] = [
    {
      id: "categories",
      label: "Хотя бы одна номинация",
      done: competition.categories.length > 0,
      sectionId: "categories",
      blocking: true,
    },
    {
      id: "disciplines",
      label: "Хотя бы одна дисциплина",
      done: competition.disciplines.length > 0,
      sectionId: "categories",
      blocking: true,
    },
    {
      id: "age-categories",
      label: "Хотя бы одна возрастная категория",
      done: competition.ageCategories.length > 0,
      sectionId: "age-categories",
      blocking: true,
    },
    {
      id: "participant-groups",
      label: "Хотя бы одна группа участников",
      done: competition.participantGroups.length > 0,
      sectionId: "participant-groups",
      blocking: true,
    },
    {
      id: "formats",
      label: "Хотя бы один формат участия",
      done: competition.enabledFormats.length > 0,
      sectionId: "participation-formats",
      blocking: true,
    },
    {
      id: "admission-rules",
      label: "Хотя бы одно правило допуска",
      done: competition.admissionRules.length > 0,
      sectionId: "admission-rules",
      blocking: true,
    },
    {
      id: "pricing",
      label: "Цены для всех комбинаций допуска",
      done:
        competition.admissionRules.length > 0 &&
        competition.admissionRules.every((rule) =>
          competition.pricingRules.some(
            (price) =>
              price.categoryId === rule.categoryId &&
              price.disciplineId === rule.disciplineId &&
              price.ageCategoryId === rule.ageCategoryId &&
              price.participantGroupId === rule.participantGroupId &&
              price.participationFormat === rule.participationFormat,
          ),
        ),
      sectionId: "pricing",
      blocking: true,
    },
    {
      id: "regulation",
      label: "Опубликованное положение",
      done:
        competition.currentRegulationId != null ||
        competition.regulations.some((regulation) => regulation.isCurrent),
      sectionId: "regulations",
      blocking: true,
    },
  ];

  const items = [...generalItems, ...taxonomyItems];
  const blockingIncomplete = items.filter((item) => item.blocking && !item.done).length;
  const generalComplete = generalItems.every((item) => item.done);

  return {
    items,
    blockingIncomplete,
    isPublishable: blockingIncomplete === 0,
    generalComplete,
  };
}
