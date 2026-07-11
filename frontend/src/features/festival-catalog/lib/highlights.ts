import { parseApiDate, registrationCutoff } from "./format";
import type { Festival } from "./types";

function time(value: string | null | undefined): number {
  return parseApiDate(value)?.getTime() ?? Number.POSITIVE_INFINITY;
}

/**
 * Pick the single festival to headline in the right panel.
 *
 * Preference: an open registration closing soonest (most urgent to act on),
 * then the nearest upcoming ("coming soon"), then simply the first available.
 */
export function selectFeatured(festivals: Festival[]): Festival | null {
  if (festivals.length === 0) {
    return null;
  }
  const open = festivals
    .filter((festival) => festival.status === "REGISTRATION_OPEN")
    .sort((a, b) => time(registrationCutoff(a)) - time(registrationCutoff(b)));
  if (open[0]) {
    return open[0];
  }
  const upcoming = festivals
    .filter((festival) => festival.status === "COMING_SOON")
    .sort((a, b) => time(a.competitionStart) - time(b.competitionStart));
  return upcoming[0] ?? festivals[0] ?? null;
}

/**
 * The "upcoming" shortlist: soon-to-happen festivals by competition date,
 * excluding the headlined one.
 */
export function selectUpcoming(
  festivals: Festival[],
  excludeId: string | null,
  limit: number,
): Festival[] {
  return festivals
    .filter((festival) => festival.id !== excludeId)
    .filter(
      (festival) => festival.status === "COMING_SOON" || festival.status === "REGISTRATION_OPEN",
    )
    .sort((a, b) => time(a.competitionStart) - time(b.competitionStart))
    .slice(0, limit);
}
