/**
 * Duration and clock formatting.
 *
 * Lives in `shared` because the organizer's programme constructor and the public
 * programme screen must render the same numbers the same way — a slot that reads
 * "3:20" for the organizer cannot read "3:20 min" beside the stage.
 */

import { FESTIVAL_TIME_ZONE } from "./festival-time";

/** ``215`` → ``"3:35"`` — a single item's length. */
export function formatDuration(totalSeconds: number): string {
  const safe = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** ``7500`` → ``"2 ч 5 мин"`` — the length of a whole programme. */
export function formatSpan(totalSeconds: number): string {
  const safe = Math.max(0, Math.round(totalSeconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.round((safe % 3600) / 60);
  if (hours === 0) {
    return `${minutes} мин`;
  }
  return minutes === 0 ? `${hours} ч` : `${hours} ч ${minutes} мин`;
}

/**
 * An ISO instant → ``"10:04"`` in the festival's zone, or ``"—"`` when untimed.
 *
 * The *festival's* zone, not the viewer's: the server renders the very same minute into
 * the cells of a public link and into the PDF, and a programme whose header and whose
 * rows disagree by three hours is worse than one with no clock at all. See
 * {@link FESTIVAL_TIME_ZONE}.
 */
export function formatClock(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: FESTIVAL_TIME_ZONE,
  });
}
