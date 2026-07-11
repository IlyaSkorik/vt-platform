import type { BadgeProps } from "@/shared/ui";

export type CompetitionStatusFilter =
  | "ALL"
  | "DRAFT"
  | "PUBLISHED"
  | "REGISTRATION_OPEN"
  | "REGISTRATION_CLOSED"
  | "COMPLETED"
  | "ARCHIVED";

export type CompetitionSortOption = "NEWEST" | "OLDEST" | "NAME";

export const STATUS_FILTER_OPTIONS: ReadonlyArray<{
  value: CompetitionStatusFilter;
  label: string;
}> = [
  { value: "ALL", label: "Все статусы" },
  { value: "DRAFT", label: "Черновик" },
  { value: "PUBLISHED", label: "Опубликован" },
  { value: "REGISTRATION_OPEN", label: "Регистрация открыта" },
  { value: "REGISTRATION_CLOSED", label: "Регистрация закрыта" },
  { value: "COMPLETED", label: "Завершён" },
  { value: "ARCHIVED", label: "В архиве" },
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
  REGISTRATION_OPEN: "Регистрация открыта",
  REGISTRATION_CLOSED: "Регистрация закрыта",
  RUNNING: "Идёт",
  COMPLETED: "Завершён",
  ARCHIVED: "В архиве",
};

const STATUS_VARIANTS: Record<string, NonNullable<BadgeProps["variant"]>> = {
  DRAFT: "neutral",
  CONFIGURED: "info",
  READY: "info",
  PUBLISHED: "primary",
  REGISTRATION_OPEN: "success",
  REGISTRATION_CLOSED: "warning",
  RUNNING: "warning",
  COMPLETED: "secondary",
  ARCHIVED: "outline",
};

export function competitionStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function competitionStatusVariant(status: string): NonNullable<BadgeProps["variant"]> {
  return STATUS_VARIANTS[status] ?? "neutral";
}

export function registrationStatusLabel(status: string): string {
  if (status === "REGISTRATION_OPEN") {
    return "Открыта";
  }
  if (status === "REGISTRATION_CLOSED") {
    return "Закрыта";
  }
  if (status === "PUBLISHED") {
    return "Ещё не открыта";
  }
  return "—";
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
