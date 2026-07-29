import { type CSSProperties, useLayoutEffect } from "react";
import type { TemplateFieldStyle } from "@/features/diplomas";
import { cn } from "@/shared/lib";

/**
 * A generic to land on while a face is still loading, or when a template names a family the
 * library no longer has. Chosen from the family's own name rather than guessed: a serif that
 * falls back to a sans re-wraps every line it was laid out against.
 */
function genericFor(family: string): string {
  return /serif/i.test(family) && !/sans/i.test(family) ? "serif" : "sans-serif";
}

const MIN_FONT_PX = 4;

/** CSS for a field's text, excluding font-size (owned imperatively by autoshrink). */
export function fieldTextStyle(style: TemplateFieldStyle, scale: number): CSSProperties {
  return {
    // Quoted, with a generic behind it: family names here contain spaces ("PT Sans"), and an
    // unquoted one with a space is not a valid CSS font-family value.
    fontFamily: `"${style.fontFamily}", ${genericFor(style.fontFamily)}`,
    fontWeight: style.fontWeight === "bold" ? 700 : 400,
    fontStyle: style.fontStyle,
    color: style.color,
    lineHeight: String(style.lineHeight),
    letterSpacing: `${style.letterSpacing * scale}px`,
    textAlign: style.textAlign,
  };
}

export function fieldTextClassName(style: TemplateFieldStyle): string {
  return cn(
    "block w-full",
    style.wrapText ? "whitespace-pre-wrap break-words" : "truncate",
    style.underline && "underline",
  );
}

/** Whether the text overflows its box (with a 1px tolerance against jitter). */
function overflows(text: HTMLElement, box: HTMLElement): boolean {
  return text.scrollWidth > text.clientWidth + 1 || text.scrollHeight > box.clientHeight + 1;
}

/**
 * Size the text imperatively: at `basePx` (= fontSize × scale), then, when
 * autoShrink is on, shrink until it fits its box. Never grows past `basePx` — a
 * larger box just means less shrinking. Shared by the editable and read-only
 * renderers so both size text identically.
 *
 * `text` (the resolved string) is a dependency because it changes the metrics —
 * without it the size would stay frozen from a previous value (switching preview
 * data, editing, a different applicant). The fit also re-runs once web fonts
 * finish loading, since their metrics differ from the fallback.
 */
export function useAutoShrinkFont(
  boxRef: React.RefObject<HTMLElement | null>,
  textRef: React.RefObject<HTMLElement | null>,
  basePx: number,
  style: TemplateFieldStyle,
  width: number,
  height: number,
  text: string,
): void {
  // biome-ignore lint/correctness/useExhaustiveDependencies: deps are the metric inputs, not the closure
  useLayoutEffect(() => {
    const textEl = textRef.current;
    const box = boxRef.current;
    if (!textEl || !box) {
      return;
    }

    const applyFit = (): void => {
      if (!style.autoShrink) {
        textEl.style.fontSize = `${basePx}px`;
        return;
      }
      let size = basePx;
      textEl.style.fontSize = `${size}px`;
      let guard = 0;
      while (overflows(textEl, box) && size > MIN_FONT_PX && guard < 400) {
        size = Math.max(MIN_FONT_PX, size - Math.max(0.5, size * 0.06));
        textEl.style.fontSize = `${size}px`;
        guard += 1;
      }
    };

    applyFit();

    // Web fonts load asynchronously; their metrics differ from the fallback, so
    // re-fit once they are ready to avoid a stale (over- or under-shrunk) size.
    let cancelled = false;
    document.fonts?.ready.then(() => {
      if (!cancelled) {
        applyFit();
      }
    });
    return () => {
      cancelled = true;
    };
  }, [
    basePx,
    style.autoShrink,
    style.wrapText,
    style.fontWeight,
    style.fontStyle,
    style.fontFamily,
    style.lineHeight,
    style.letterSpacing,
    width,
    height,
    text,
  ]);
}
