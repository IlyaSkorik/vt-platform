import type {
  _AgeCategory,
  _Category,
  AddAgeCategory,
  MixedCalculationMethodEnum,
  PatchedUpdateAgeCategory,
  TypeEnum,
} from "@/shared/api/generated/model-competitions";
import {
  TypeEnum as AgeTypes,
  MixedCalculationMethodEnum as MixedMethods,
} from "@/shared/api/generated/model-competitions";

export type AgeCategoryKind = TypeEnum;
export type MixedAgeMethod = MixedCalculationMethodEnum;

export const AGE_CATEGORY_TYPE_LABELS: Record<AgeCategoryKind, string> = {
  STANDARD: "Стандартная",
  MIXED: "Смешанная",
};

export const MIXED_AGE_METHOD_LABELS: Record<MixedAgeMethod, string> = {
  AVERAGE: "Средний возраст участников",
  OLDEST: "По старшему участнику",
  YOUNGEST: "По младшему участнику",
};

export const AGE_CATEGORY_TYPE_OPTIONS = [
  { value: AgeTypes.STANDARD, label: AGE_CATEGORY_TYPE_LABELS.STANDARD },
  { value: AgeTypes.MIXED, label: AGE_CATEGORY_TYPE_LABELS.MIXED },
] as const;

export const MIXED_AGE_METHOD_OPTIONS = [
  { value: MixedMethods.AVERAGE, label: MIXED_AGE_METHOD_LABELS.AVERAGE },
  { value: MixedMethods.OLDEST, label: MIXED_AGE_METHOD_LABELS.OLDEST },
  { value: MixedMethods.YOUNGEST, label: MIXED_AGE_METHOD_LABELS.YOUNGEST },
] as const;

export interface AgeCategoryNominationNode {
  nomination: _Category;
  ageCategories: _AgeCategory[];
}

export function sortAgeCategories(items: _AgeCategory[]): _AgeCategory[] {
  return [...items].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    if (left.minAge !== right.minAge) {
      return left.minAge - right.minAge;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

export function sortNominations(items: _Category[]): _Category[] {
  return [...items].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

export function buildAgeCategoryTree(
  nominations: _Category[],
  ageCategories: _AgeCategory[],
): AgeCategoryNominationNode[] {
  return sortNominations(nominations).map((nomination) => ({
    nomination,
    ageCategories: sortAgeCategories(
      ageCategories.filter((item) => item.categoryId === nomination.id),
    ),
  }));
}

export function filterAgeCategoryTree(
  tree: AgeCategoryNominationNode[],
  search: string,
): AgeCategoryNominationNode[] {
  const query = search.trim().toLowerCase();
  if (query.length === 0) {
    return tree;
  }

  return tree
    .map((node) => {
      const nominationMatches = node.nomination.name.toLowerCase().includes(query);
      const matched = node.ageCategories.filter((item) => {
        const methodLabel =
          item.mixedCalculationMethod != null
            ? (MIXED_AGE_METHOD_LABELS[item.mixedCalculationMethod as MixedAgeMethod] ?? "")
            : "";
        const haystack =
          `${item.name} ${formatAgeRange(item.minAge, item.maxAge)} ${methodLabel}`.toLowerCase();
        return haystack.includes(query);
      });
      if (nominationMatches) {
        return node;
      }
      if (matched.length > 0) {
        return { ...node, ageCategories: matched };
      }
      return null;
    })
    .filter((node): node is AgeCategoryNominationNode => node != null);
}

export function formatAgeRange(minAge: number, maxAge: number): string {
  if (maxAge >= 99) {
    return `${minAge}+`;
  }
  if (minAge === maxAge) {
    return `${minAge}`;
  }
  return `${minAge}–${maxAge}`;
}

export function formatAgeRangeLabel(minAge: number, maxAge: number): string {
  return `${formatAgeRange(minAge, maxAge)} лет`;
}

export function nextAgeCategorySortOrder(items: _AgeCategory[], categoryId: string): number {
  const scoped = items.filter((item) => item.categoryId === categoryId);
  if (scoped.length === 0) {
    return 0;
  }
  return Math.max(...scoped.map((item) => item.sortOrder)) + 1;
}

export function suggestAgeCategoryName(minAge: number, maxAge: number): string {
  return formatAgeRangeLabel(minAge, maxAge);
}

export function duplicateAgeCategoryDraft(item: _AgeCategory): {
  categoryId: string;
  name: string;
  minAge: number;
  maxAge: number;
  type: AgeCategoryKind;
  mixedCalculationMethod: MixedAgeMethod | null;
} {
  return {
    categoryId: item.categoryId,
    name: `${item.name} (копия)`,
    minAge: item.minAge,
    maxAge: item.maxAge,
    type: (item.type as AgeCategoryKind) || AgeTypes.STANDARD,
    mixedCalculationMethod: (item.mixedCalculationMethod as MixedAgeMethod | null) ?? null,
  };
}

export function buildAgeCategoryReorderUpdates(
  orderedIds: string[],
  items: _AgeCategory[],
): Array<{ ageCategoryId: string; payload: PatchedUpdateAgeCategory }> {
  const byId = new Map(items.map((item) => [item.id, item]));
  const updates: Array<{ ageCategoryId: string; payload: PatchedUpdateAgeCategory }> = [];

  orderedIds.forEach((ageCategoryId, index) => {
    const item = byId.get(ageCategoryId);
    if (!item || item.sortOrder === index) {
      return;
    }
    updates.push({ ageCategoryId, payload: { sortOrder: index } });
  });

  return updates;
}

export function createAgeCategoryPayload(values: {
  categoryId: string;
  name: string;
  minAge: number;
  maxAge: number;
  type: AgeCategoryKind;
  mixedCalculationMethod: MixedAgeMethod | null;
  sortOrder?: number;
}): AddAgeCategory {
  return {
    categoryId: values.categoryId,
    name: values.name.trim(),
    minAge: values.minAge,
    maxAge: values.maxAge,
    type: values.type,
    mixedCalculationMethod: values.type === AgeTypes.MIXED ? values.mixedCalculationMethod : null,
    ...(values.sortOrder != null ? { sortOrder: values.sortOrder } : {}),
  };
}

export function updateAgeCategoryPayload(values: {
  name: string;
  minAge: number;
  maxAge: number;
  type: AgeCategoryKind;
  mixedCalculationMethod: MixedAgeMethod | null;
}): PatchedUpdateAgeCategory {
  return {
    name: values.name.trim(),
    minAge: values.minAge,
    maxAge: values.maxAge,
    type: values.type,
    mixedCalculationMethod: values.type === AgeTypes.MIXED ? values.mixedCalculationMethod : null,
  };
}

export function moveIdBefore(orderedIds: string[], draggedId: string, targetId: string): string[] {
  if (draggedId === targetId) {
    return orderedIds;
  }
  const withoutDragged = orderedIds.filter((id) => id !== draggedId);
  const targetIndex = withoutDragged.indexOf(targetId);
  if (targetIndex === -1) {
    return orderedIds;
  }
  const next = [...withoutDragged];
  next.splice(targetIndex, 0, draggedId);
  return next;
}
