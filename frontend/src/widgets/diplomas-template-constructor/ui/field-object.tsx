import type { TemplateField } from "@/features/diplomas";
import type { FieldRect } from "../model/use-constructor-fields";
import { useFieldMovement } from "../model/use-field-movement";
import { FieldRenderer } from "./field-renderer";
import { ResizeHandles } from "./resize-handles";

interface FieldObjectProps {
  field: TemplateField;
  overlayRef: React.RefObject<HTMLDivElement | null>;
  selected: boolean;
  /** Preview text resolved from the field's binding. */
  displayValue: string;
  /** Current display scale, forwarded to the renderer for font sizing. */
  scale: number;
  onSelect: () => void;
  onMove: (x: number, y: number) => void;
  onResize: (rect: FieldRect) => void;
}

/**
 * Composes the per-field layers: FieldMovement (body drag + select) and
 * FieldResize (corner handles) over the FieldRenderer view. The overlay owns the
 * data wiring; this only assembles behaviour + view for one field.
 */
export function FieldObject({
  field,
  overlayRef,
  selected,
  displayValue,
  scale,
  onSelect,
  onMove,
  onResize,
}: FieldObjectProps): React.JSX.Element {
  const bodyProps = useFieldMovement({ field, overlayRef, onSelect, onMove });
  return (
    <FieldRenderer
      field={field}
      selected={selected}
      displayValue={displayValue}
      scale={scale}
      bodyProps={bodyProps}
      handles={<ResizeHandles field={field} overlayRef={overlayRef} onResize={onResize} />}
    />
  );
}
