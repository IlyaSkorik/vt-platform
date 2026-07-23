import { useRef } from "react";
import type { TemplateField } from "@/features/diplomas";

interface UseFieldMovementArgs {
  field: TemplateField;
  /** The page overlay — the coordinate space drags are normalised against. */
  overlayRef: React.RefObject<HTMLDivElement | null>;
  onSelect: () => void;
  onMove: (x: number, y: number) => void;
}

interface DragState {
  pointerX: number;
  pointerY: number;
  originX: number;
  originY: number;
  overlayWidth: number;
  overlayHeight: number;
}

export interface FieldPointerHandlers {
  onPointerDown: (event: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerMove: (event: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerUp: (event: React.PointerEvent<HTMLButtonElement>) => void;
}

/**
 * FieldMovement: turns a body drag into normalised move deltas and a press into
 * selection. Pointer capture keeps the drag smooth outside the element. Holds no
 * geometry — clamping to the page lives in the data layer.
 */
export function useFieldMovement({
  field,
  overlayRef,
  onSelect,
  onMove,
}: UseFieldMovementArgs): FieldPointerHandlers {
  const drag = useRef<DragState | null>(null);

  return {
    onPointerDown: (event) => {
      event.stopPropagation();
      onSelect();
      const rect = overlayRef.current?.getBoundingClientRect();
      if (!rect || rect.width === 0 || rect.height === 0) {
        return;
      }
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = {
        pointerX: event.clientX,
        pointerY: event.clientY,
        originX: field.x,
        originY: field.y,
        overlayWidth: rect.width,
        overlayHeight: rect.height,
      };
    },
    onPointerMove: (event) => {
      const state = drag.current;
      if (state === null) {
        return;
      }
      onMove(
        state.originX + (event.clientX - state.pointerX) / state.overlayWidth,
        state.originY + (event.clientY - state.pointerY) / state.overlayHeight,
      );
    },
    onPointerUp: (event) => {
      if (drag.current === null) {
        return;
      }
      drag.current = null;
      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        // Pointer already released — safe to ignore.
      }
    },
  };
}
