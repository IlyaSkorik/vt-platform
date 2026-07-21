/**
 * Helpers for treating an external document URL (Google Docs/Drive, or any
 * `http(s)` link) as an embeddable, stable reference.
 *
 * The point of a link source is convenience: an organizer pastes one URL that
 * never changes, then keeps editing the underlying document in Google Docs —
 * the platform always points at the live document, never a stale copy.
 */

/** True for any absolute `http(s)` URL (i.e. an external link, not a stored media path). */
export function isExternalDocLink(reference: string | null | undefined): boolean {
  return /^https?:\/\//i.test(reference?.trim() ?? "");
}

/** True when the URL points at Google Docs, Sheets, Slides or Drive. */
export function isGoogleDocsUrl(reference: string | null | undefined): boolean {
  const value = reference?.trim();
  if (!value) {
    return false;
  }
  try {
    const host = new URL(value).hostname.toLowerCase();
    return host === "docs.google.com" || host === "drive.google.com";
  } catch {
    return false;
  }
}

const GOOGLE_DOC =
  /^(https:\/\/docs\.google\.com\/(?:document|spreadsheets|presentation)\/d\/[^/?#]+)/i;
const DRIVE_FILE = /^https:\/\/drive\.google\.com\/file\/d\/([^/?#]+)/i;
const DRIVE_OPEN = /^https:\/\/drive\.google\.com\/open\?[^#]*\bid=([^&#]+)/i;

/**
 * Rewrite a Google Docs/Drive share URL into its embeddable `/preview` form so
 * it can be shown inside an `<iframe>`. Already-embeddable URLs (`/preview`,
 * published `/pub`) and non-Google links are returned unchanged.
 */
export function toEmbeddableDocUrl(reference: string | null | undefined): string | null {
  const value = reference?.trim();
  if (!value) {
    return null;
  }
  if (/\/preview(?:[/?#]|$)/i.test(value) || /\/pub(?:[/?#]|$)/i.test(value)) {
    return value;
  }
  const doc = GOOGLE_DOC.exec(value);
  if (doc) {
    return `${doc[1]}/preview`;
  }
  const driveFile = DRIVE_FILE.exec(value);
  if (driveFile) {
    return `https://drive.google.com/file/d/${driveFile[1]}/preview`;
  }
  const driveOpen = DRIVE_OPEN.exec(value);
  if (driveOpen) {
    return `https://drive.google.com/file/d/${driveOpen[1]}/preview`;
  }
  return value;
}
