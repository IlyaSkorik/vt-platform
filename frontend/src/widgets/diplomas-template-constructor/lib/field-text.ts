import { type CSSProperties, useLayoutEffect } from "react";
import type { TemplateFieldStyle } from "@/features/diplomas";
import { cn } from "@/shared/lib";

const MIN_FONT_PX = 4;

/** CSS for a field's text, excluding font-size (owned imperatively by autoshrink). */
export function fieldTextStyle(style: TemplateFieldStyle, scale: number): CSSProperties {
  return {
    fontFamily: style.fontFamily,
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

/**
 * Size the text imperatively: at `basePx` (= fontSize × scale), then, when
 * autoShrink is on, shrink until it fits its box. Shared by the editable and
 * read-only renderers so both size text identically.
 */
export function useAutoShrinkFont(
  boxRef: React.RefObject<HTMLElement | null>,
  textRef: React.RefObject<HTMLElement | null>,
  basePx: number,
  style: TemplateFieldStyle,
  width: number,
  height: number,
): void {
  // biome-ignore lint/correctness/useExhaustiveDependencies: deps drive text metrics, not the closure
  useLayoutEffect(() => {
    const text = textRef.current;
    const box = boxRef.current;
    if (!text || !box) {
      return;
    }
    if (!style.autoShrink) {
      text.style.fontSize = `${basePx}px`;
      return;
    }
    let size = basePx;
    text.style.fontSize = `${size}px`;
    let guard = 0;
    while (
      (text.scrollWidth > box.clientWidth || text.scrollHeight > box.clientHeight) &&
      size > MIN_FONT_PX &&
      guard < 400
    ) {
      size -= Math.max(0.5, size * 0.06);
      text.style.fontSize = `${size}px`;
      guard += 1;
    }
  }, [
    basePx,
    style.autoShrink,
    style.wrapText,
    style.fontWeight,
    style.fontStyle,
    style.lineHeight,
    style.letterSpacing,
    width,
    height,
  ]);
}
