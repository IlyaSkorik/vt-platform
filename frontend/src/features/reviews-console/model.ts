/**
 * The console's side of a review page, as rules rather than as markup.
 *
 * Pure functions over the payload, so what the screen says — and what it offers to
 * copy — is testable without rendering anything.
 */
import type { Review } from "./api";

/**
 * The public address of a review page, for the QR and for reading aloud.
 *
 * Absolute because it goes onto a banner and into a chat, where a relative path
 * means nothing.
 */
export function publicReviewUrl(slug: string, origin?: string): string {
  const base = origin ?? (typeof window === "undefined" ? "" : window.location.origin);
  return `${base}/reviews/${slug}`;
}

/** How a note is signed in a list, when it is not signed at all. */
export function authorLabel(review: Review): string {
  return review.authorName?.trim() || "Без подписи";
}

/**
 * What an organizer should know before printing the code.
 *
 * The honest version: the page takes anything anybody writes, and nothing on it is
 * verified. That is the trade an open link makes, and an organizer who does not
 * know it will read the first piece of abuse as a platform failure.
 */
export const OPEN_LINK_NOTE =
  "Ссылка открыта всем, у кого есть код: отзыв может оставить любой, и имя в нём не проверяется. " +
  "Ничего из собранного не публикуется — отзывы видите вы и оператор платформы.";
