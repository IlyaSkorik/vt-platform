import { useRef } from "react";
import type { TemplateField } from "@/features/diplomas";
import { cn } from "@/shared/lib";
import { MIN_HEIGHT, MIN_WIDTH } from "../model/field-factory";
import type { FieldRect } from "../model/use-constructor-fields";

type Corner = "nw" | "ne" | "sw" | "se";

const CORNERS: ReadonlyArray<{ id: Corner; className: string; cursor: string }> = [
  { id: "nw", className: "-left-1 -top-1", cursor: "cursor-nwse-resize" },
  { id: "ne", className: "-right-1 -top-1", cursor: "cursor-nesw-resize" },
  { id: "sw", className: "-bottom-1 -left-1", cursor: "cursor-nesw-resize" },
  { id: "se", className: "-right-1 -bottom-1", cursor: "cursor-nwse-resize" },
];

interface DragState {
  pointerX: number;
  pointerY: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
  overlayWidth: number;
  overlayHeight: number;
  corner: Corner;
}

interface ResizeHandlesProps {
  field: TemplateField;
  overlayRef: React.RefObject<HTMLDivElement | null>;
  onResize: (rect: FieldRect) => void;
}

/**
 * FieldResize: four corner handles that resize the active field by moving its
 * edges. Produces a normalised rect (page-relative), enforcing the minimum size
 * by pushing the dragged edge back and clamping to the page bounds.
 */
export function ResizeHandles({
  field,
  overlayRef,
  onResize,
}: ResizeHandlesProps): React.JSX.Element {
  const drag = useRef<DragState | null>(null);

  const onPointerDown =
    (corner: Corner) =>
    (event: React.PointerEvent<HTMLButtonElement>): void => {
      event.stopPropagation();
      const rect = overlayRef.current?.getBoundingClientRect();
      if (!rect || rect.width === 0 || rect.height === 0) {
        return;
      }
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = {
        pointerX: event.clientX,
        pointerY: event.clientY,
        left: field.x,
        top: field.y,
        right: field.x + field.width,
        bottom: field.y + field.height,
        overlayWidth: rect.width,
        overlayHeight: rect.height,
        corner,
      };
    };

  const onPointerMove = (event: React.PointerEvent<HTMLButtonElement>): void => {
    const state = drag.current;
    if (state === null) {
      return;
    }
    const dx = (event.clientX - state.pointerX) / state.overlayWidth;
    const dy = (event.clientY - state.pointerY) / state.overlayHeight;
    const movesLeft = state.corner === "nw" || state.corner === "sw";
    const movesTop = state.corner === "nw" || state.corner === "ne";

    let left = movesLeft ? state.left + dx : state.left;
    let right = movesLeft ? state.right : state.right + dx;
    let top = movesTop ? state.top + dy : state.top;
    let bottom = movesTop ? state.bottom : state.bottom + dy;

    // Clamp to the page, then enforce the minimum size on the dragged edge.
    left = Math.max(0, left);
    top = Math.max(0, top);
    right = Math.min(1, right);
    bottom = Math.min(1, bottom);
    if (movesLeft) {
      left = Math.min(left, right - MIN_WIDTH);
    } else {
      right = Math.max(right, left + MIN_WIDTH);
    }
    if (movesTop) {
      top = Math.min(top, bottom - MIN_HEIGHT);
    } else {
      bottom = Math.max(bottom, top + MIN_HEIGHT);
    }

    onResize({ x: left, y: top, width: right - left, height: bottom - top });
  };

  const onPointerUp = (event: React.PointerEvent<HTMLButtonElement>): void => {
    if (drag.current === null) {
      return;
    }
    drag.current = null;
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // Pointer already released — safe to ignore.
    }
  };

  return (
    <>
      {CORNERS.map((corner) => (
        <button
          key={corner.id}
          type="button"
          aria-label={`Изменить размер (${corner.id})`}
          onPointerDown={onPointerDown(corner.id)}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          className={cn(
            "pointer-events-auto absolute z-10 size-2.5 touch-none rounded-full border border-primary bg-background",
            corner.className,
            corner.cursor,
          )}
        />
      ))}
    </>
  );
}
