import { useRef } from "react";
import { resolveFieldDisplay } from "@/features/diplomas";
import { useConstructorFieldsContext } from "../model/fields-context";
import { usePreviewData } from "../model/preview-context";
import { FieldObject } from "./field-object";

interface CanvasOverlayProps {
  pageNumber: number;
  /** Current display scale, forwarded to fields for font sizing. */
  scale: number;
}

/**
 * Transparent layer stacked over a page's PDF canvas — the editor's work area.
 * All constructor elements live here as separate DOM nodes with page-relative
 * (normalised) coordinates; the PDF underneath is never drawn on.
 *
 * The overlay itself is `pointer-events-none` so empty areas let the viewer
 * scroll and pass background clicks through (deselection is handled there); each
 * field opts back into pointer events. This element is also the coordinate space
 * drags/resizes are normalised against.
 */
export function CanvasOverlay({ pageNumber, scale }: CanvasOverlayProps): React.JSX.Element {
  const overlayRef = useRef<HTMLDivElement>(null);
  const { fields, selectedId, selectField, moveField, resizeField } = useConstructorFieldsContext();
  const { resolve } = usePreviewData();
  const pageFields = fields.filter((field) => field.page === pageNumber);

  return (
    <div
      ref={overlayRef}
      data-overlay-page={pageNumber}
      className="pointer-events-none absolute inset-0 z-10"
    >
      {pageFields.map((field) => (
        <FieldObject
          key={field.id}
          field={field}
          overlayRef={overlayRef}
          scale={scale}
          displayValue={resolveFieldDisplay(field, resolve)}
          selected={field.id === selectedId}
          onSelect={() => selectField(field.id)}
          onMove={(x, y) => moveField(field.id, x, y)}
          onResize={(rect) => resizeField(field.id, rect)}
        />
      ))}
    </div>
  );
}
