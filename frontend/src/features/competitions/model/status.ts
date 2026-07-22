import type { BadgeProps } from "@/shared/ui";

export type CompetitionStatusFilter = "ALL" | "DRAFT" | "PUBLISHED" | "RUNNING" | "COMPLETED";

export type CompetitionSortOption = "NEWEST" | "OLDEST" | "NAME";

export const STATUS_FILTER_OPTIONS: ReadonlyArray<{
  value: CompetitionStatusFilter;
  label: string;
}> = [
  { value: "ALL", label: "Все статусы" },
  { value: "DRAFT", label: "Черновик" },
  { value: "PUBLISHED", label: "Опубликован" },
  { value: "RUNNING", label: "Идёт" },
  { value: "COMPLETED", label: "Завершён" },
];

export const SORT_OPTIONS: ReadonlyArray<{ value: CompetitionSortOption; label: string }> = [
  { value: "NEWEST", label: "Сначала новые" },
  { value: "OLDEST", label: "Сначала старые" },
  { value: "NAME", label: "По названию" },
];

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Черновик",
  CONFIGURED: "Настроен",
  READY: "Готов",
  PUBLISHED: "Опубликован",
  RUNNING: "Идёт",
  COMPLETED: "Завершён",
};

const STATUS_VARIANTS: Record<string, NonNullable<BadgeProps["variant"]>> = {
  DRAFT: "neutral",
  CONFIGURED: "info",
  READY: "info",
  PUBLISHED: "primary",
  RUNNING: "success",
  COMPLETED: "secondary",
};

export function competitionStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function competitionStatusVariant(status: string): NonNullable<BadgeProps["variant"]> {
  return STATUS_VARIANTS[status] ?? "neutral";
}

/** Map UI filter values to backend status codes (includes intermediate states). */
export function matchesStatusFilter(status: string, filter: CompetitionStatusFilter): boolean {
  if (filter === "ALL") {
    return true;
  }
  if (filter === "PUBLISHED") {
    return status === "PUBLISHED" || status === "CONFIGURED" || status === "READY";
  }
  return status === filter;
}
