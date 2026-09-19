/**
 * The form's own rules, as functions rather than as markup.
 *
 * They exist twice on purpose — here and on the server — because the copy here is
 * the one that can say "эта фотография слишком большая" before somebody spends a
 * minute uploading it over a hall's wifi. The server's copy is the one that
 * decides.
 */

/** How many photographs may travel with one note (the server's limit, mirrored). */
export const MAX_PHOTOS = 5;

/** The longest note the page accepts. Generous: this is a phone in a foyer. */
export const MAX_TEXT = 4000;

/** What the upload endpoint will keep, by what the file is rather than its name. */
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"];

const MAX_BYTES = 8 * 1024 * 1024;

/**
 * Why this file cannot be attached, or `null` when it can.
 *
 * Checked before anything is sent, so the answer arrives immediately rather than
 * after the whole file has crossed the network to be refused.
 */
export function photoProblem(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type.toLowerCase())) {
    return `«${file.name}» — не фотография. Подойдут JPEG, PNG, WebP или HEIC.`;
  }
  if (file.size > MAX_BYTES) {
    return `«${file.name}» тяжелее ${MAX_BYTES / (1024 * 1024)} МБ.`;
  }
  return null;
}
