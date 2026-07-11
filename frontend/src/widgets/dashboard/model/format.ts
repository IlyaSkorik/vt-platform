/**
 * Presentation helpers for the dashboard: ru-RU number/date formatting and the
 * domain-status → UI (label + badge variant) mappings.
 *
 * All user-facing strings are Russian (primary locale, NFR-15). `Intl`
 * formatters are created once at module load (they are expensive to construct)
 * and reused, so widgets never hand-roll locale logic.
 */

import type { BadgeProps } from "@/shared/ui";
import type {
  ApplicationStatus,
  CompetitionStatus,
  EventKind,
  StatKey,
  TrendDirection,
} from "./types";

const LOCALE = "ru-RU";

const integerFormatter = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });
const percentFormatter = new Intl.NumberFormat(LOCALE, {
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});
const dateFormatter = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "long" });
const relativeFormatter = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });

/** Format a whole number with locale grouping (e.g. `1 240`). */
export function formatNumber(value: number): string {
  return integerFormatter.format(value);
}

/**
 * Format an amount held in minor units as localized currency.
 * `12345` + `BYN` → `123,45 Br`. Never operates on floats.
 */
export function formatMoney(minorUnits: number, currency: string): string {
  const formatter = new Intl.NumberFormat(LOCALE, { style: "currency", currency });
  return formatter.format(minorUnits / 100);
}

/** Signed percentage for a delta chip (e.g. `+12,5 %`, `−4 %`). */
export function formatPercent(value: number): string {
  return `${percentFormatter.format(value)} %`;
}

/** Absolute short date (e.g. `8 июля`). */
export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

/**
 * Coarse relative time from now (e.g. `2 часа назад`, `через 3 дня`).
 * Picks the largest sensible unit so the feed reads naturally.
 */
export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const diffMs = new Date(iso).getTime() - now.getTime();
  const diffSec = Math.round(diffMs / 1000);
  const abs = Math.abs(diffSec);

  const units: readonly [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3600],
    ["minute", 60],
  ];

  for (const [unit, seconds] of units) {
    if (abs >= seconds) {
      return relativeFormatter.format(Math.round(diffSec / seconds), unit);
    }
  }
  return relativeFormatter.format(diffSec, "second");
}

/** Trend arrow glyph for a stat delta (decorative; paired with a text label). */
export const TREND_GLYPH: Record<TrendDirection, string> = {
  up: "↑",
  down: "↓",
  flat: "→",
};

/** Russian labels for the five headline metrics. */
export const STAT_LABELS: Record<StatKey, string> = {
  participants: "Участники",
  competitions: "Фестивали",
  applications: "Заявки",
  results: "Результаты",
  finance: "Финансы",
};

interface StatusPresentation {
  readonly label: string;
  readonly variant: NonNullable<BadgeProps["variant"]>;
}

/** Competition status → Russian label + badge tone. */
export const COMPETITION_STATUS: Record<CompetitionStatus, StatusPresentation> = {
  draft: { label: "Черновик", variant: "neutral" },
  published: { label: "Опубликован", variant: "info" },
  open: { label: "Открыт", variant: "info" },
  submission: { label: "Приём заявок", variant: "primary" },
  judging: { label: "Судейство", variant: "warning" },
  results: { label: "Результаты", variant: "success" },
  archived: { label: "В архиве", variant: "neutral" },
  cancelled: { label: "Отменён", variant: "danger" },
};

/** Application status → Russian label + badge tone. */
export const APPLICATION_STATUS: Record<ApplicationStatus, StatusPresentation> = {
  draft: { label: "Черновик", variant: "neutral" },
  submitted: { label: "Подана", variant: "info" },
  under_review: { label: "На рассмотрении", variant: "warning" },
  accepted: { label: "Принята", variant: "success" },
  rejected: { label: "Отклонена", variant: "danger" },
  waitlisted: { label: "Лист ожидания", variant: "secondary" },
  withdrawn: { label: "Отозвана", variant: "neutral" },
};

/** Russian labels for scheduled event kinds. */
export const EVENT_KIND_LABELS: Record<EventKind, string> = {
  submission_deadline: "Дедлайн приёма заявок",
  judging_start: "Начало судейства",
  results: "Публикация результатов",
  live_slot: "Живое выступление",
  reminder: "Напоминание",
};
