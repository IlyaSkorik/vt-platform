const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/**
 * Format a publication instant as a Russian date **with the time of day**.
 *
 * Always with the time, never a bare date: a festival publishes several nominations in one
 * afternoon and corrects one of them an hour later, so "26 авг. 2026" cannot tell two
 * revisions apart and the ordering an organizer reads off the screen would be a guess.
 */
export function formatPublishedAt(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return DATE_TIME_FORMATTER.format(parsed);
}
