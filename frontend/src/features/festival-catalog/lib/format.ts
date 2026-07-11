import { CLOSING_SOON_DAYS, type Festival } from "./types";

const DAY_MS = 24 * 60 * 60 * 1000;

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const dayMonthFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
});

const priceFormatter = new Intl.NumberFormat("ru-RU", {
  maximumFractionDigits: 2,
});

/**
 * Parse a backend date/datetime string into a local `Date`.
 *
 * Date-only values (`YYYY-MM-DD`) are built from local components so a card never
 * shows the previous day in western time zones (a naive `new Date("2026-07-12")`
 * is parsed as UTC midnight). Returns `null` for empty/invalid input.
 */
export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Date(Number(year), Number(month) - 1, Number(day));
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDate(value: string | null | undefined): string | null {
  const date = parseApiDate(value);
  return date ? dateFormatter.format(date) : null;
}

/** Render a competition-date range compactly ("12–14 июл 2026"). */
export function formatPeriod(
  start: string | null | undefined,
  end: string | null | undefined,
): string | null {
  const startDate = parseApiDate(start);
  const endDate = parseApiDate(end);
  if (!startDate && !endDate) {
    return null;
  }
  if (startDate && !endDate) {
    return dateFormatter.format(startDate);
  }
  if (!startDate && endDate) {
    return dateFormatter.format(endDate);
  }
  if (startDate && endDate) {
    if (startDate.getTime() === endDate.getTime()) {
      return dateFormatter.format(startDate);
    }
    const sameYear = startDate.getFullYear() === endDate.getFullYear();
    const startLabel = sameYear
      ? dayMonthFormatter.format(startDate)
      : dateFormatter.format(startDate);
    return `${startLabel} – ${dateFormatter.format(endDate)}`;
  }
  return null;
}

/** Format the "from X" price summary, or `null` when no price is configured. */
export function formatPrice(festival: Festival): string | null {
  const { amountFrom, currency, multiple } = festival.pricing;
  if (amountFrom == null) {
    return null;
  }
  const numeric = Number(amountFrom);
  if (Number.isNaN(numeric)) {
    return null;
  }
  const amount = priceFormatter.format(numeric);
  const money = currency ? `${amount} ${currency}` : amount;
  return multiple ? `от ${money}` : money;
}

/** The effective registration cut-off: an explicit application deadline, else the window end. */
export function registrationCutoff(festival: Festival): string | null {
  return festival.applicationDeadline ?? festival.registrationEnd ?? null;
}

/** Whole days from `now` until `value` (negative if past); `null` if unset. */
export function daysUntil(value: string | null | undefined, now: Date): number | null {
  const date = parseApiDate(value);
  if (!date) {
    return null;
  }
  return Math.ceil((date.getTime() - now.getTime()) / DAY_MS);
}

/**
 * A competition is "closing soon" when registration is open and its cut-off is
 * within the {@link CLOSING_SOON_DAYS} window (and not already past).
 */
export function isClosingSoon(festival: Festival, now: Date): boolean {
  if (festival.status !== "REGISTRATION_OPEN") {
    return false;
  }
  const days = daysUntil(registrationCutoff(festival), now);
  return days != null && days >= 0 && days <= CLOSING_SOON_DAYS;
}

/** Human label for the registration deadline shown in the card footer. */
export function formatDeadline(festival: Festival): string | null {
  return formatDate(registrationCutoff(festival));
}
