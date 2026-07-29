/**
 * Load the diploma fonts into the document so the editor draws with the same files the PDF
 * embeds.
 *
 * The constructor sets `font-family: "Montserrat"` on a field and the browser has no
 * Montserrat, so before this existed the canvas fell back to a system sans while the renderer
 * used the real face. Everything downstream of that — where a line wraps, whether a name fits
 * its box, what the organizer approved — was measured against the wrong font.
 *
 * One `<style>` element, keyed by its own id so React strict-mode double-invocation and
 * several mounted editors share it instead of stacking duplicates. It is deliberately *not*
 * removed on unmount: the rules are idempotent, the files are cached, and tearing them down
 * would make a font-loading flash out of every navigation between the constructor and its
 * preview.
 */
import { useEffect } from "react";

import { useFontCatalog } from "../api/fonts-api";
import { type FontFamily, fontFaceCss } from "../model/fonts";

const STYLE_ELEMENT_ID = "vt-diploma-font-faces";

/** Inject (or refresh) the `@font-face` rules for a catalog. Exported for tests. */
export function applyFontFaces(families: readonly FontFamily[]): void {
  if (typeof document === "undefined") {
    return;
  }
  const css = fontFaceCss(families);
  if (!css) {
    return;
  }
  let element = document.getElementById(STYLE_ELEMENT_ID);
  if (element == null) {
    element = document.createElement("style");
    element.id = STYLE_ELEMENT_ID;
    document.head.appendChild(element);
  }
  // Replaced wholesale rather than appended: an upload re-runs this with the fuller catalog,
  // and appending would leave the previous generation's rules behind it.
  if (element.textContent !== css) {
    element.textContent = css;
  }
}

/**
 * Make every catalog family renderable in this document.
 *
 * Call it once where diploma text is drawn — the constructor and its preview. Returns the
 * catalog's families so a caller that also needs to resolve a font stack does not have to
 * read the query twice.
 */
export function useFontFaces(): FontFamily[] {
  const { data } = useFontCatalog();
  const families = data?.families ?? [];

  useEffect(() => {
    applyFontFaces(families);
  }, [families]);

  return families;
}
