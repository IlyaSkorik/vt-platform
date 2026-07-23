import { useRef } from "react";
import type { TemplateField } from "@/features/diplomas";
import { fieldTextClassName, fieldTextStyle, useAutoShrinkFont } from "../lib/field-text";

interface PreviewFieldRendererProps {
  field: TemplateField;
  /** Resolved value from the BindingResolver (or the field's own text). */
  displayValue: string;
  scale: number;
}

/**
 * Read-only field view for the diploma preview: same geometry and appearance as
 * the editor's FieldRenderer (shared via `lib/field-text`), but no border,
 * selection or interaction — just the resolved text over the PDF.
 */
export function PreviewFieldRenderer({
  field,
  displayValue,
  scale,
}: PreviewFieldRendererProps): React.JSX.Element {
  const { style } = field;
  const boxRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  useAutoShrinkFont(boxRef, textRef, style.fontSize * scale, style, field.width, field.height);

  return (
    <div
      ref={boxRef}
      className="absolute flex items-center overflow-hidden px-1"
      style={{
        left: `${field.x * 100}%`,
        top: `${field.y * 100}%`,
        width: `${field.width * 100}%`,
        height: `${field.height * 100}%`,
      }}
    >
      <span
        ref={textRef}
        className={fieldTextClassName(style)}
        style={fieldTextStyle(style, scale)}
      >
        {displayValue}
      </span>
    </div>
  );
}
