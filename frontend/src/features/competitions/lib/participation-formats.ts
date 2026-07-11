import type {
  _ParticipationFormat,
  AddParticipationFormat,
  PatchedUpdateParticipationFormat,
} from "@/shared/api/generated/model-competitions";

export function sortParticipationFormats(items: _ParticipationFormat[]): _ParticipationFormat[] {
  return [...items].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

export function filterParticipationFormats(
  items: _ParticipationFormat[],
  search: string,
): _ParticipationFormat[] {
  const query = search.trim().toLowerCase();
  if (query.length === 0) {
    return sortParticipationFormats(items);
  }
  return sortParticipationFormats(items).filter((item) => {
    const haystack = `${item.name} ${item.description ?? ""}`.toLowerCase();
    return haystack.includes(query);
  });
}

export function nextParticipationFormatSortOrder(items: _ParticipationFormat[]): number {
  if (items.length === 0) {
    return 0;
  }
  return Math.max(...items.map((item) => item.sortOrder)) + 1;
}

export function duplicateParticipationFormatDraft(item: _ParticipationFormat): {
  name: string;
  description: string;
  enabled: boolean;
} {
  return {
    name: `${item.name} (копия)`,
    description: item.description ?? "",
    enabled: item.enabled,
  };
}

export function buildParticipationFormatReorderUpdates(
  orderedIds: string[],
  items: _ParticipationFormat[],
): Array<{ formatId: string; payload: PatchedUpdateParticipationFormat }> {
  const byId = new Map(items.map((item) => [item.id, item]));
  const updates: Array<{ formatId: string; payload: PatchedUpdateParticipationFormat }> = [];

  orderedIds.forEach((formatId, index) => {
    const item = byId.get(formatId);
    if (!item || item.sortOrder === index) {
      return;
    }
    updates.push({ formatId, payload: { sortOrder: index } });
  });

  return updates;
}

export function createParticipationFormatPayload(values: {
  name: string;
  description?: string;
  enabled?: boolean;
  sortOrder?: number;
}): AddParticipationFormat {
  const description = values.description?.trim() ?? "";
  return {
    name: values.name.trim(),
    description: description.length > 0 ? description : null,
    enabled: values.enabled ?? true,
    ...(values.sortOrder != null ? { sortOrder: values.sortOrder } : {}),
  };
}

export function updateParticipationFormatPayload(values: {
  name: string;
  description?: string;
  enabled?: boolean;
}): PatchedUpdateParticipationFormat {
  const description = values.description?.trim() ?? "";
  return {
    name: values.name.trim(),
    description: description.length > 0 ? description : null,
    ...(values.enabled != null ? { enabled: values.enabled } : {}),
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

export function countEnabledFormats(items: _ParticipationFormat[]): number {
  return items.filter((item) => item.enabled).length;
}
