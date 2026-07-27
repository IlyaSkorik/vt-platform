const DATE_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Format an ISO timestamp as a short Russian date; empty string when absent. */
export function formatDate(iso: string | null | undefined): string {
  return format(iso, DATE_FORMATTER);
}

/**
 * Same, with the time of day — for events that happen several times a day.
 *
 * The generation archive needs it: a competition is generated, re-generated and
 * re-printed within one afternoon, and a bare date cannot order those runs.
 */
export function formatDateTime(iso: string | null | undefined): string {
  return format(iso, DATE_TIME_FORMATTER);
}

function format(iso: string | null | undefined, formatter: Intl.DateTimeFormat): string {
  if (!iso) {
    return "";
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return formatter.format(parsed);
}
