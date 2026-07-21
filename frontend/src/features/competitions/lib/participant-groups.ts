import type {
  _ParticipantGroup,
  AddParticipantGroup,
  PatchedUpdateParticipantGroup,
} from "@/shared/api/generated/model-competitions";

export function sortParticipantGroups(items: _ParticipantGroup[]): _ParticipantGroup[] {
  return [...items].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    if (left.minCount !== right.minCount) {
      return left.minCount - right.minCount;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

/** Filter the competition-wide group list by a free-text query, keeping sort order. */
export function filterParticipantGroups(
  items: _ParticipantGroup[],
  search: string,
): _ParticipantGroup[] {
  const sorted = sortParticipantGroups(items);
  const query = search.trim().toLowerCase();
  if (query.length === 0) {
    return sorted;
  }
  return sorted.filter((item) => {
    const haystack =
      `${item.name} ${formatParticipantRange(item.minCount, item.maxCount)} ${item.description ?? ""}`.toLowerCase();
    return haystack.includes(query);
  });
}

export function formatParticipantRange(minCount: number, maxCount: number | null): string {
  if (maxCount == null) {
    return `${minCount}+`;
  }
  if (minCount === maxCount) {
    return `${minCount}`;
  }
  return `${minCount}–${maxCount}`;
}

export function formatParticipantRangeLabel(minCount: number, maxCount: number | null): string {
  const range = formatParticipantRange(minCount, maxCount);
  if (maxCount == null) {
    return `${range} участников`;
  }
  if (minCount === maxCount) {
    const mod10 = minCount % 10;
    const mod100 = minCount % 100;
    if (mod10 === 1 && mod100 !== 11) return `${range} участник`;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${range} участника`;
    return `${range} участников`;
  }
  return `${range} участников`;
}

export function nextParticipantGroupSortOrder(items: _ParticipantGroup[]): number {
  if (items.length === 0) {
    return 0;
  }
  return Math.max(...items.map((item) => item.sortOrder)) + 1;
}

export function duplicateParticipantGroupDraft(item: _ParticipantGroup): {
  name: string;
  minCount: number;
  maxCount: number | null;
  description: string;
} {
  return {
    name: `${item.name} (копия)`,
    minCount: item.minCount,
    maxCount: item.maxCount,
    description: item.description ?? "",
  };
}

export function buildParticipantGroupReorderUpdates(
  orderedIds: string[],
  items: _ParticipantGroup[],
): Array<{ participantGroupId: string; payload: PatchedUpdateParticipantGroup }> {
  const byId = new Map(items.map((item) => [item.id, item]));
  const updates: Array<{ participantGroupId: string; payload: PatchedUpdateParticipantGroup }> = [];

  orderedIds.forEach((participantGroupId, index) => {
    const item = byId.get(participantGroupId);
    if (!item || item.sortOrder === index) {
      return;
    }
    updates.push({ participantGroupId, payload: { sortOrder: index } });
  });

  return updates;
}

export function createParticipantGroupPayload(values: {
  name: string;
  minCount: number;
  maxCount: number | null;
  description?: string;
  sortOrder?: number;
}): AddParticipantGroup {
  const description = values.description?.trim() ?? "";
  return {
    name: values.name.trim(),
    minCount: values.minCount,
    maxCount: values.maxCount,
    description: description.length > 0 ? description : null,
    ...(values.sortOrder != null ? { sortOrder: values.sortOrder } : {}),
  };
}

export function updateParticipantGroupPayload(values: {
  name: string;
  minCount: number;
  maxCount: number | null;
  description?: string;
}): PatchedUpdateParticipantGroup {
  const description = values.description?.trim() ?? "";
  return {
    name: values.name.trim(),
    minCount: values.minCount,
    maxCount: values.maxCount,
    description: description.length > 0 ? description : null,
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
