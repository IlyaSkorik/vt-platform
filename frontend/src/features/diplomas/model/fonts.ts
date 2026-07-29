/**
 * The fonts a diploma may be set in.
 *
 * The list is **served by the API**, not declared here, and that is the whole point: the
 * backend can only draw the faces it has files for, so a family that reaches this dropdown is
 * a family the PDF will actually use. It used to be seven hard-coded names, none of which the
 * renderer had — every diploma came out in DejaVu no matter what the editor showed.
 *
 * The editor also has to *display* the same files, not merely name them. A browser has no
 * Montserrat unless something gives it one, so every family carries the URL of each of its
 * faces and {@link fontFaceCss} turns the catalog into `@font-face` rules. Without that the
 * canvas previews in a system fallback while the PDF embeds the real thing — the same
 * mismatch as before, just in the other direction.
 */
import { resolveMediaUrl } from "../lib/media-url";

/** One of the four faces a family is used in. Mirrors the backend's `FontVariant`. */
export type FontVariantId = "Regular" | "Bold" | "Italic" | "BoldItalic";

/** Where a family came from — which is also whether it can be deleted. */
export type FontSource = "BUNDLED" | "UPLOADED";

/** One face of a family, with the URL the browser loads it from. */
export interface FontVariantFace {
  variant: FontVariantId;
  bold: boolean;
  italic: boolean;
  /**
   * Public by necessity: a browser fetches an `@font-face` source without the Authorization
   * header, so a font behind a token would never load here.
   */
  fileUrl: string;
}

/** One family the editor may offer. */
export interface FontFamily {
  family: string;
  source: FontSource;
  variants: FontVariantFace[];
  /**
   * Set when this name is drawn with a different family — the proprietary names (Arial,
   * Times New Roman, Georgia) that no licence lets the platform ship. Shown in the dropdown
   * so the substitution is visible rather than a surprise on the printed page.
   */
  substitutedBy: string | null;
  id: string | null;
}

/** One uploaded file, as the library screen lists it. */
export interface UploadedFont {
  id: string;
  family: string;
  variant: FontVariantId;
  originalFilename: string;
  fileUrl: string;
  sizeBytes: number;
  uploadedAt: string;
}

export interface FontCatalog {
  families: FontFamily[];
  uploaded: UploadedFont[];
}

/** The weight `@font-face` should bind a variant to. */
function cssWeight(face: FontVariantFace): number {
  return face.bold ? 700 : 400;
}

/**
 * Turn the catalog into `@font-face` rules the editor can render with.
 *
 * One rule per face, all four bound to the same `font-family` name so the browser picks the
 * right file from `font-weight`/`font-style` exactly as the PDF renderer picks it from the
 * bold/italic flags. A family that only uploaded a regular face gets one rule, and the
 * browser then synthesizes a bold — which is a visible difference from the PDF, where a
 * missing bold falls back to the real regular. Nothing can be done about that from here; it
 * is why the library screen says which variants a family is missing.
 *
 * Substituted names are skipped: "Arial" is drawn with Liberation Sans, and emitting a rule
 * that binds the *name* Arial to Liberation Sans files would work but hide the substitution
 * from the browser's own font inspector. The dropdown resolves the name instead.
 */
export function fontFaceCss(families: readonly FontFamily[]): string {
  const rules: string[] = [];
  for (const family of families) {
    if (family.substitutedBy != null) {
      continue;
    }
    for (const face of family.variants) {
      const url = resolveMediaUrl(face.fileUrl);
      if (url == null) {
        continue;
      }
      rules.push(
        [
          "@font-face {",
          `  font-family: ${JSON.stringify(family.family)};`,
          `  src: url(${JSON.stringify(url)}) format("truetype");`,
          `  font-weight: ${cssWeight(face)};`,
          `  font-style: ${face.italic ? "italic" : "normal"};`,
          // The canvas must not flash unstyled text while a face loads: the geometry is
          // measured from it, so a swap moves the field the organizer is dragging.
          "  font-display: block;",
          "}",
        ].join("\n"),
      );
    }
  }
  return rules.join("\n\n");
}

/**
 * The CSS `font-family` value to render a chosen family with.
 *
 * A substituted name has no `@font-face` of its own, so it resolves to the family that does.
 * Returned as a stack rather than a bare name so a family that has not loaded yet — or one
 * removed from the library after a template was saved — still lands on something sane.
 */
export function cssFontStack(families: readonly FontFamily[], chosen: string): string {
  const match = families.find((family) => family.family === chosen);
  const target = match?.substitutedBy ?? match?.family ?? chosen;
  const generic = /serif/i.test(target) && !/sans/i.test(target) ? "serif" : "sans-serif";
  return `${JSON.stringify(target)}, ${generic}`;
}

/** Which of the four faces a family is missing, for the library screen to say so. */
export function missingVariants(family: FontFamily): FontVariantId[] {
  const present = new Set(family.variants.map((variant) => variant.variant));
  return (["Regular", "Bold", "Italic", "BoldItalic"] as FontVariantId[]).filter(
    (variant) => !present.has(variant),
  );
}

/** How a variant is named on screen. */
export const FONT_VARIANT_LABELS: Record<FontVariantId, string> = {
  Regular: "Обычный",
  Bold: "Жирный",
  Italic: "Курсив",
  BoldItalic: "Жирный курсив",
};

/** A file size a person can read. */
export function formatFontSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} Б`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} КБ`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}
