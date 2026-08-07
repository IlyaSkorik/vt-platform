/**
 * Conversions between the wire format and a `Date`.
 *
 * The wire format is what the native inputs these pickers replace already
 * produced — `YYYY-MM-DD` for a date, `YYYY-MM-DDTHH:mm` for a date and time —
 * so every form, payload mapper and test around them keeps working untouched.
 * That is the whole reason for pinning it: the pickers are a change of control,
 * not a change of contract.
 *
 * Everything here is deliberately **local-time and string-based**. `new Date("2015-04-01")`
 * parses as midnight UTC, which in any timezone behind UTC is the 31st of March —
 * that is how a birth date silently loses a day. Building the date from its parts
 * keeps it the day the user picked.
 */

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const TIME_PATTERN = /^(\d{1,2}):(\d{2})$/;

const displayFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "long",
  year: "numeric",
});

/** `2015-04-01` → a local `Date`, or `undefined` when there is nothing valid to parse. */
export function parseDateValue(value: string | null | undefined): Date | undefined {
  const match = DATE_PATTERN.exec((value ?? "").trim());
  if (match == null) {
    return undefined;
  }
  const [, year, month, day] = match;
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  // Rejects the impossible dates the pattern happily matches (`2015-02-31`):
  // JavaScript rolls those over into March rather than refusing them.
  if (date.getMonth() !== Number(month) - 1 || date.getDate() !== Number(day)) {
    return undefined;
  }
  return date;
}

/** A local `Date` → `2015-04-01`. */
export function formatDateValue(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/** `2015-04-01` → `01 апреля 2015 г.` for the trigger's label. */
export function formatDateLabel(value: string | null | undefined): string | null {
  const date = parseDateValue(value);
  return date == null ? null : displayFormatter.format(date);
}

/** Split `2026-05-20T18:30` into its two halves; either may be absent. */
export function splitDateTime(value: string | null | undefined): { date: string; time: string } {
  const [date = "", time = ""] = (value ?? "").trim().split("T");
  return { date, time: time.slice(0, 5) };
}

/**
 * Rejoin a date and a time into the `datetime-local` shape.
 *
 * A time with no date is nothing — there is no instant to name — so it collapses
 * to an empty value. A date with no time keeps midnight rather than being thrown
 * away, because "the 20th" is a complete enough answer to save while the user is
 * still working out the hour.
 */
export function joinDateTime(date: string, time: string): string {
  if (!date) {
    return "";
  }
  return `${date}T${normaliseTime(time) || "00:00"}`;
}

/**
 * `9:5` → `09:05`, `25:00` → `""`.
 *
 * Typed input arrives half-finished and in whatever shape the person's keyboard
 * produced; this is what decides whether it is yet a time at all.
 */
export function normaliseTime(value: string): string {
  const match = TIME_PATTERN.exec(value.trim());
  if (match == null) {
    return "";
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) {
    return "";
  }
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}
