import { useLayoutEffect, useRef } from "react";
import type { TemplateField } from "@/features/diplomas";
import { cn } from "@/shared/lib";
import { FIELD_PLACEHOLDERS } from "../model/field-factory";
import type { FieldPointerHandlers } from "../model/use-field-movement";

interface FieldRendererProps {
  field: TemplateField;
  selected: boolean;
  /** Current display scale — 1 PDF point renders at `scale` CSS px (pdf.js). */
  scale: number;
  /** Body (move + select) pointer handlers from FieldMovement. */
  bodyProps: FieldPointerHandlers;
  /** Resize handles (FieldResize), rendered only when selected. */
  handles: React.ReactNode;
}

const MIN_FONT_PX = 4;

/**
 * View layer: draws a field from its normalised geometry (percent box on the
 * overlay) and its appearance. Font size is in PDF points → `fontSize * scale`
 * px, so text tracks zoom exactly. AutoShrink measures the rendered text against
 * its box and reduces the size to fit. The PDF underneath is never touched.
 */
export function FieldRenderer({
  field,
  selected,
  scale,
  bodyProps,
  handles,
}: FieldRendererProps): React.JSX.Element {
  const { style } = field;
  const boxRef = useRef<HTMLButtonElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const basePx = style.fontSize * scale;

  // Font size is applied imperatively (React never sets it) so autoShrink can
  // measure and reduce it without fighting a controlled style prop. The style /
  // geometry deps all change the measured fit, so they must retrigger it.
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
    field.width,
    field.height,
  ]);

  return (
    <div
      className="pointer-events-none absolute"
      style={{
        left: `${field.x * 100}%`,
        top: `${field.y * 100}%`,
        width: `${field.width * 100}%`,
        height: `${field.height * 100}%`,
        zIndex: selected ? 2 : 1,
      }}
    >
      <button
        ref={boxRef}
        type="button"
        aria-label={FIELD_PLACEHOLDERS[field.type]}
        aria-pressed={selected}
        onPointerDown={bodyProps.onPointerDown}
        onPointerMove={bodyProps.onPointerMove}
        onPointerUp={bodyProps.onPointerUp}
        className={cn(
          "pointer-events-auto absolute inset-0 flex cursor-move touch-none select-none items-center overflow-hidden px-1 outline-none",
          selected
            ? "border-2 border-primary bg-primary/5"
            : "border border-neutral-400/70 border-dashed hover:border-primary/60",
        )}
      >
        <span
          ref={textRef}
          className={cn(
            "block w-full",
            style.wrapText ? "whitespace-pre-wrap break-words" : "truncate",
            style.underline && "underline",
          )}
          style={{
            fontFamily: style.fontFamily,
            fontWeight: style.fontWeight === "bold" ? 700 : 400,
            fontStyle: style.fontStyle,
            color: style.color,
            lineHeight: String(style.lineHeight),
            letterSpacing: `${style.letterSpacing * scale}px`,
            textAlign: style.textAlign,
          }}
        >
          {FIELD_PLACEHOLDERS[field.type]}
        </span>
      </button>
      {selected ? handles : null}
    </div>
  );
}
