/**
 * The zone a programme is written and read in.
 *
 * A programme is a wall clock, not an instant: «начало в 10:00» is a fact about the hall,
 * and it has to read 10:00 for the organizer who typed it, on the link handed to the
 * audience, and on the PDF pinned up backstage. Those three are rendered in three
 * different places — the browser, the server's cell renderer, and reportlab — so the only
 * way they agree is if all three name the same zone instead of each using its own.
 *
 * Previously the browser used the viewer's zone and the server used UTC, which is why a
 * programme that read 10:00 in the constructor came out 07:00 on its public link.
 * The backend's half of this pact is `apps.programs.application.rendering.DISPLAY_TZ`.
 */

/** Where the festivals are held. Keep in step with the backend's `DISPLAY_TZ`. */
export const FESTIVAL_TIME_ZONE = "Europe/Minsk";

/** The parts of `date` as they read on the wall in `timeZone`. */
function zonedParts(date: Date, timeZone: string): Record<string, number> {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const parts: Record<string, number> = {};
  for (const part of formatter.formatToParts(date)) {
    if (part.type !== "literal") {
      // `hour` comes back as 24 at midnight under `hour12: false` in some engines, and
      // reading it as 0 is the whole of that correction. **Only the hour** — applying it
      // to every part turned the 24th of the month into the 0th, so a programme held on
      // the 24th came back as `2026-10-00`, which is not a date: the field could not
      // parse it and showed nothing. It set, it vanished, it set again, it vanished
      // again — and only ever on a day, or a minute, that happened to be 24.
      parts[part.type] = part.type === "hour" && part.value === "24" ? 0 : Number(part.value);
    }
  }
  return parts;
}

/** How far `timeZone` is ahead of UTC at `date`, in milliseconds. */
function offsetMs(date: Date, timeZone: string): number {
  const parts = zonedParts(date, timeZone);
  const asIfUtc = Date.UTC(
    parts.year ?? 1970,
    (parts.month ?? 1) - 1,
    parts.day ?? 1,
    parts.hour ?? 0,
    parts.minute ?? 0,
    parts.second ?? 0,
  );
  return asIfUtc - date.getTime();
}

/**
 * `"2026-08-01T10:00"` typed in the festival's zone → the ISO instant to store.
 *
 * Two passes: the first offset is read at the wrong instant whenever the typed time sits
 * on a DST change, and applying it lands close enough that the second read is the right
 * one. Minsk has no DST today, so this only matters if the constant ever moves.
 */
export function festivalInputToIso(
  localValue: string,
  timeZone = FESTIVAL_TIME_ZONE,
): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(localValue);
  if (!match) {
    return null;
  }
  const [, year, month, day, hour, minute] = match.map(Number) as number[];
  const naive = Date.UTC(year ?? 0, (month ?? 1) - 1, day ?? 1, hour ?? 0, minute ?? 0);
  const first = new Date(naive - offsetMs(new Date(naive), timeZone));
  const corrected = new Date(naive - offsetMs(first, timeZone));
  return Number.isNaN(corrected.getTime()) ? null : corrected.toISOString();
}

/**
 * An ISO instant → `"2026-08-01T10:00"` as it reads in the festival's zone.
 *
 * The inverse of {@link festivalInputToIso}, and what a `datetime-local` input wants.
 */
export function isoToFestivalInput(iso: string | null, timeZone = FESTIVAL_TIME_ZONE): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const parts = zonedParts(date, timeZone);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${parts.year}-${pad(parts.month ?? 1)}-${pad(parts.day ?? 1)}T${pad(parts.hour ?? 0)}:${pad(parts.minute ?? 0)}`;
}
