import { useRef } from "react";
import type { TemplateField } from "@/features/diplomas";
import { cn } from "@/shared/lib";
import { fieldTextClassName, fieldTextStyle, useAutoShrinkFont } from "../lib/field-text";
import type { FieldPointerHandlers } from "../model/use-field-movement";
import { QrBlockView } from "./qr-block-view";

interface FieldRendererProps {
  field: TemplateField;
  selected: boolean;
  /** Ready-to-draw text from the display-value layer — no platform knowledge here. */
  displayValue: string;
  /** Current display scale — 1 PDF point renders at `scale` CSS px (pdf.js). */
  scale: number;
  /** Body (move + select) pointer handlers from FieldMovement. */
  bodyProps: FieldPointerHandlers;
  /** Resize handles (FieldResize), rendered only when selected. */
  handles: React.ReactNode;
}

/**
 * View layer (editable): draws a field from its normalised geometry (percent box
 * on the overlay) and its appearance. Font sizing/appearance is shared with the
 * read-only preview via `lib/field-text`. The PDF underneath is never touched.
 */
export function FieldRenderer({
  field,
  selected,
  displayValue,
  scale,
  bodyProps,
  handles,
}: FieldRendererProps): React.JSX.Element {
  const { style } = field;
  const boxRef = useRef<HTMLButtonElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  useAutoShrinkFont(boxRef, textRef, style.fontSize * scale, style, field.width, field.height);

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
        aria-label={displayValue}
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
        {field.type === "qr_block" ? (
          <QrBlockView number={displayValue} style={style} scale={scale} />
        ) : (
          <span
            ref={textRef}
            className={fieldTextClassName(style)}
            style={fieldTextStyle(style, scale)}
          >
            {displayValue}
          </span>
        )}
      </button>
      {selected ? handles : null}
    </div>
  );
}
