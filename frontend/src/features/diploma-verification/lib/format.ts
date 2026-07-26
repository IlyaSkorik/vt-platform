const MONTH_YEAR_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

/** `dd.mm.yyyy`, the shape the diploma snapshot stores a competition date in. */
const SNAPSHOT_DATE = /^(\d{2})\.(\d{2})\.(\d{4})$/;

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/**
 * Render a competition date the way a document reads it: "12 апреля 2026".
 *
 * The snapshot froze this as a display string (`dd.mm.yyyy`), so it is reformatted
 * rather than parsed from a timestamp. Anything that is not that exact shape is
 * returned verbatim — a snapshot is immutable and may predate the current format,
 * and showing what was frozen always beats showing nothing.
 */
export function formatCompetitionDate(value: string | null | undefined): string | null {
  const text = value?.trim();
  if (!text) {
    return null;
  }
  const match = SNAPSHOT_DATE.exec(text);
  if (match == null) {
    return text;
  }
  const [, day, month, year] = match;
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  if (Number.isNaN(date.getTime()) || date.getMonth() !== Number(month) - 1) {
    return text;
  }
  // ru-RU renders "12 апреля 2026 г."; the trailing era marker is noise here.
  return MONTH_YEAR_FORMATTER.format(date).replace(/\s*г\.$/, "");
}

/**
 * Stamp the moment of this check: "26.07.2026 18:42".
 *
 * Deliberately client-side and deliberately local — it records when *this
 * visitor* consulted the registry, which is not something the backend can know
 * or should be asked for.
 */
export function formatCheckedAt(at: Date): string {
  return `${pad(at.getDate())}.${pad(at.getMonth() + 1)}.${at.getFullYear()} ${pad(at.getHours())}:${pad(at.getMinutes())}`;
}
