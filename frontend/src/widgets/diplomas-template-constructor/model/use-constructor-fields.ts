import { useCallback, useMemo, useState } from "react";
import type {
  TemplateField,
  TemplateFieldConfig,
  TemplateFieldStyle,
  TemplateFieldTypeId,
} from "@/features/diplomas";
import { createField, DUPLICATE_OFFSET, MIN_HEIGHT, MIN_WIDTH } from "./field-factory";

/** The subset of a field's geometry the inspector can edit numerically. */
export type FieldGeometryPatch = Partial<
  Pick<TemplateField, "page" | "x" | "y" | "width" | "height">
>;

/** A normalised box; the geometry a resize produces. */
export interface FieldRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

function clampPosition(value: number, size: number): number {
  return Math.min(Math.max(0, value), Math.max(0, 1 - size));
}

/** Clamp a rect to the page and enforce the minimum size. */
function normalizeRect(rect: FieldRect): FieldRect {
  const width = Math.min(1, Math.max(MIN_WIDTH, rect.width));
  const height = Math.min(1, Math.max(MIN_HEIGHT, rect.height));
  return {
    width,
    height,
    x: clampPosition(rect.x, width),
    y: clampPosition(rect.y, height),
  };
}

export interface ConstructorFieldsState {
  fields: TemplateField[];
  selectedId: string | null;
  selectedField: TemplateField | null;
  /** True when the layout differs from the last saved/loaded state (DirtyTracker). */
  dirty: boolean;
  /** Add a new field of `type`, centred on `page` (defaults to page 1). */
  addField: (type: TemplateFieldTypeId, page?: number) => void;
  /** Move a field to normalised (x, y); clamped so it stays on the page. */
  moveField: (id: string, x: number, y: number) => void;
  /** Resize a field to a normalised rect; clamped to the page and min size. */
  resizeField: (id: string, rect: FieldRect) => void;
  /** Remove a field (and clear the selection if it was selected). */
  removeField: (id: string) => void;
  /** Duplicate a field, offset it slightly, and select the copy. */
  duplicateField: (id: string) => void;
  /** Patch a field's geometry (inspector inputs); clamped to page + min size. */
  updateGeometry: (id: string, patch: FieldGeometryPatch) => void;
  /** Patch a field's appearance (inspector controls). */
  updateStyle: (id: string, patch: Partial<TemplateFieldStyle>) => void;
  /** Set a free-text field's own text. */
  updateValue: (id: string, value: string) => void;
  /** Patch a composite field's config (nomination block parts/prefix). */
  updateConfig: (id: string, patch: Partial<TemplateFieldConfig>) => void;
  selectField: (id: string) => void;
  deselect: () => void;
  /** Replace the whole layout and mark it clean (e.g. on load or discard). */
  initialize: (fields: TemplateField[]) => void;
  /** Mark the current layout as saved (clears the dirty flag). */
  markPristine: () => void;
}

/**
 * The editor's data layer (ConstructorState) plus a DirtyTracker. Holds the
 * placed fields, the selection and a dirty flag — normalised coordinates only,
 * no DOM, no network. Geometry invariants (page bounds, minimum size) live here;
 * every mutation flips `dirty`, cleared by load (`initialize`) and save
 * (`markPristine`).
 */
export function useConstructorFields(initialFields: TemplateField[]): ConstructorFieldsState {
  const [fields, setFields] = useState<TemplateField[]>(initialFields);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const addField = useCallback((type: TemplateFieldTypeId, page = 1) => {
    const field = createField(type, page);
    setFields((prev) => [...prev, field]);
    setSelectedId(field.id);
    setDirty(true);
  }, []);

  const moveField = useCallback((id: string, x: number, y: number) => {
    setFields((prev) =>
      prev.map((field) =>
        field.id === id
          ? { ...field, x: clampPosition(x, field.width), y: clampPosition(y, field.height) }
          : field,
      ),
    );
    setDirty(true);
  }, []);

  const resizeField = useCallback((id: string, rect: FieldRect) => {
    setFields((prev) =>
      prev.map((field) => (field.id === id ? { ...field, ...normalizeRect(rect) } : field)),
    );
    setDirty(true);
  }, []);

  const removeField = useCallback((id: string) => {
    setFields((prev) => prev.filter((field) => field.id !== id));
    setSelectedId((current) => (current === id ? null : current));
    setDirty(true);
  }, []);

  const duplicateField = useCallback((id: string) => {
    setFields((prev) => {
      const source = prev.find((field) => field.id === id);
      if (!source) {
        return prev;
      }
      const copy: TemplateField = {
        ...source,
        id: createField(source.type, source.page).id,
        x: clampPosition(source.x + DUPLICATE_OFFSET, source.width),
        y: clampPosition(source.y + DUPLICATE_OFFSET, source.height),
      };
      setSelectedId(copy.id);
      return [...prev, copy];
    });
    setDirty(true);
  }, []);

  const updateGeometry = useCallback((id: string, patch: FieldGeometryPatch) => {
    setFields((prev) =>
      prev.map((field) => {
        if (field.id !== id) {
          return field;
        }
        const merged = { ...field, ...patch };
        const rect = normalizeRect({
          x: merged.x,
          y: merged.y,
          width: merged.width,
          height: merged.height,
        });
        return { ...merged, ...rect, page: Math.max(1, Math.floor(merged.page)) };
      }),
    );
    setDirty(true);
  }, []);

  const updateStyle = useCallback((id: string, patch: Partial<TemplateFieldStyle>) => {
    setFields((prev) =>
      prev.map((field) =>
        field.id === id ? { ...field, style: { ...field.style, ...patch } } : field,
      ),
    );
    setDirty(true);
  }, []);

  const updateValue = useCallback((id: string, value: string) => {
    setFields((prev) => prev.map((field) => (field.id === id ? { ...field, value } : field)));
    setDirty(true);
  }, []);

  const updateConfig = useCallback((id: string, patch: Partial<TemplateFieldConfig>) => {
    setFields((prev) =>
      prev.map((field) =>
        field.id === id ? { ...field, config: { ...field.config, ...patch } } : field,
      ),
    );
    setDirty(true);
  }, []);

  const selectField = useCallback((id: string) => setSelectedId(id), []);
  const deselect = useCallback(() => setSelectedId(null), []);

  const initialize = useCallback((next: TemplateField[]) => {
    setFields(next);
    setSelectedId(null);
    setDirty(false);
  }, []);

  const markPristine = useCallback(() => setDirty(false), []);

  const selectedField = useMemo(
    () => fields.find((field) => field.id === selectedId) ?? null,
    [fields, selectedId],
  );

  return {
    fields,
    selectedId,
    selectedField,
    dirty,
    addField,
    moveField,
    resizeField,
    removeField,
    duplicateField,
    updateGeometry,
    updateStyle,
    updateValue,
    updateConfig,
    selectField,
    deselect,
    initialize,
    markPristine,
  };
}
