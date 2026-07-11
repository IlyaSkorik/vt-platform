import type { _Period } from "@/shared/api/generated/model-competitions";

const DATE_FORMAT: Intl.DateTimeFormatOptions = {
  day: "2-digit",
  month: "short",
  year: "numeric",
};

const DATETIME_FORMAT: Intl.DateTimeFormatOptions = {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", DATE_FORMAT).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", DATETIME_FORMAT).format(date);
}

export function formatPeriod(period: _Period | null | undefined): string {
  if (period?.start == null || period.end == null) {
    return "Даты не указаны";
  }
  return `${formatDate(period.start)} — ${formatDate(period.end)}`;
}

export function defaultSeason(): string {
  const year = new Date().getFullYear();
  return `${year}/${year + 1}`;
}
