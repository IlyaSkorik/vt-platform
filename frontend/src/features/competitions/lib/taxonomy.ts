import type {
  _Category,
  _Discipline,
  AddCategory,
  AddDiscipline,
  PatchedRenameCategory,
  PatchedRenameDiscipline,
} from "@/shared/api/generated/model-competitions";

export interface TaxonomyCategoryNode {
  category: _Category;
  disciplines: _Discipline[];
}

export function sortCategories(categories: _Category[]): _Category[] {
  return [...categories].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

export function sortDisciplines(disciplines: _Discipline[]): _Discipline[] {
  return [...disciplines].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

export function buildTaxonomyTree(
  categories: _Category[],
  disciplines: _Discipline[],
): TaxonomyCategoryNode[] {
  return sortCategories(categories).map((category) => ({
    category,
    disciplines: sortDisciplines(
      disciplines.filter((discipline) => discipline.categoryId === category.id),
    ),
  }));
}

export function filterTaxonomyTree(
  tree: TaxonomyCategoryNode[],
  search: string,
): TaxonomyCategoryNode[] {
  const query = search.trim().toLowerCase();
  if (query.length === 0) {
    return tree;
  }

  return tree
    .map((node) => {
      const categoryMatches =
        node.category.name.toLowerCase().includes(query) ||
        (node.category.description ?? "").toLowerCase().includes(query);
      const matchedDisciplines = node.disciplines.filter((discipline) =>
        discipline.name.toLowerCase().includes(query),
      );

      if (categoryMatches) {
        return node;
      }
      if (matchedDisciplines.length > 0) {
        return { ...node, disciplines: matchedDisciplines };
      }
      return null;
    })
    .filter((node): node is TaxonomyCategoryNode => node != null);
}

export function nextCategorySortOrder(categories: _Category[]): number {
  if (categories.length === 0) {
    return 0;
  }
  return Math.max(...categories.map((category) => category.sortOrder)) + 1;
}

export function nextDisciplineSortOrder(disciplines: _Discipline[], categoryId: string): number {
  const scoped = disciplines.filter((discipline) => discipline.categoryId === categoryId);
  if (scoped.length === 0) {
    return 0;
  }
  return Math.max(...scoped.map((discipline) => discipline.sortOrder)) + 1;
}

export function buildCategoryReorderUpdates(
  orderedIds: string[],
  categories: _Category[],
): Array<{ categoryId: string; payload: PatchedRenameCategory }> {
  const byId = new Map(categories.map((category) => [category.id, category]));
  const updates: Array<{ categoryId: string; payload: PatchedRenameCategory }> = [];

  orderedIds.forEach((categoryId, index) => {
    const category = byId.get(categoryId);
    if (!category || category.sortOrder === index) {
      return;
    }
    updates.push({ categoryId, payload: { sortOrder: index } });
  });

  return updates;
}

export function buildDisciplineReorderUpdates(
  orderedIds: string[],
  disciplines: _Discipline[],
): Array<{ disciplineId: string; payload: PatchedRenameDiscipline }> {
  const byId = new Map(disciplines.map((discipline) => [discipline.id, discipline]));
  const updates: Array<{ disciplineId: string; payload: PatchedRenameDiscipline }> = [];

  orderedIds.forEach((disciplineId, index) => {
    const discipline = byId.get(disciplineId);
    if (!discipline || discipline.sortOrder === index) {
      return;
    }
    updates.push({ disciplineId, payload: { sortOrder: index } });
  });

  return updates;
}

export function createCategoryPayload(values: {
  name: string;
  description?: string;
  sortOrder?: number;
}): AddCategory {
  const description = values.description?.trim() ?? "";
  return {
    name: values.name.trim(),
    description: description.length > 0 ? description : null,
    ...(values.sortOrder != null ? { sortOrder: values.sortOrder } : {}),
  };
}

export function createDisciplinePayload(values: {
  categoryId: string;
  name: string;
  sortOrder?: number;
}): AddDiscipline {
  return {
    categoryId: values.categoryId,
    name: values.name.trim(),
    ...(values.sortOrder != null ? { sortOrder: values.sortOrder } : {}),
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
