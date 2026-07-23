import type { TemplateField } from "./constructor";

/**
 * Resolves a binding key to a display string. Two implementations exist — the
 * editor's PreviewDataProvider (sample values) and the preview's BindingResolver
 * (real applicant values) — and the renderer works with either, unchanged.
 */
export type BindingResolveFn = (binding: string) => string;

/** Placeholder for a binding with no value — the UI must never crash on a gap. */
export const MISSING_VALUE = "—";

/**
 * The single rule for a field's on-screen text: a data-bound field resolves via
 * the provider, a free field shows its own value. Shared by editor and preview.
 */
export function resolveFieldDisplay(field: TemplateField, resolve: BindingResolveFn): string {
  if (field.binding) {
    return resolve(field.binding);
  }
  return field.value ?? "";
}

/** BindingResolver from a resolved binding→value map; missing keys render as "—". */
export function createBindingResolver(bindings: Record<string, string>): BindingResolveFn {
  return (binding) => {
    const value = bindings[binding];
    return value !== undefined && value !== "" ? value : MISSING_VALUE;
  };
}
