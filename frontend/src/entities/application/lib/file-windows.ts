/**
 * Whether the applicant may still touch the files of an entry, and why not.
 *
 * Three cards ask this — фонограммы, видео и фото, документы на льготу — and they
 * ask it about three different windows of the same festival. Keeping the question
 * here rather than in each card is what stops the three from drifting into three
 * slightly different answers, which on this screen reads as the platform not
 * knowing its own rules.
 *
 * **The dates are not consulted.** The projection already carries the answer per
 * kind (`musicUploadOpen` and friends), computed by the backend from the deadline,
 * the organizer's freeze and whether the festival is over. Recomputing it here from
 * `deadlines` would be a second implementation of a rule that has three inputs and
 * only one of them is a date.
 */
import type { Registration } from "@/shared/api/generated/model-public-catalog";

/**
 * Submission statuses in which the platform still takes files — the whole live path
 * of an entry, mirroring ``_LIVE_STATUSES`` in the Applications domain.
 *
 * A running order is built only from entries that are ACCEPTED or beyond, and a
 * track is wanted right up to the day, so anything narrower would leave the sound
 * desk's archive empty.
 */
const LIVE_STATUSES = new Set([
  "DRAFT",
  "SUBMITTED",
  "UNDER_REVIEW",
  "REQUIRES_CORRECTION",
  "APPROVED",
  "WAITING_PAYMENT",
  "PAID",
  "ACCEPTED",
  "SCHEDULED",
]);

/** Which window a card is about. */
export type FileWindow = "music" | "media" | "document";

/**
 * Why files of this kind cannot be changed right now, or `null` when they can.
 *
 * `undefined` while the projection is still loading answers `null` — the controls
 * stay as they are and the server, which owns the rule, refuses if it has to. The
 * alternative is a card that flickers from "закрыто" to "открыто" on every load.
 */
export function fileWindowClosedReason(
  registration: Registration | undefined,
  window: FileWindow,
): string | null {
  if (!registration) {
    return null;
  }
  // The freeze first: an applicant looking at an upload deadline that is still a
  // week away would read «срок истёк» as a bug, and it would send them to argue
  // about dates with the person who did not change any.
  if (registration.editingLocked) {
    return "Организатор закрыл редактирование заявок. Файлы больше не меняются — напишите организатору.";
  }
  const open = {
    music: registration.musicUploadOpen,
    media: registration.mediaUploadOpen,
    document: registration.documentUploadOpen,
  }[window];
  return open ? null : "Срок загрузки файлов этого типа истёк. Напишите организатору.";
}

/** Whether this entry is still at a point in its life where files are taken. */
export function acceptsFiles(status: string): boolean {
  return LIVE_STATUSES.has(status);
}
