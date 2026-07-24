import { NOMINATION_PARTS, type TemplateField, type TemplateFieldConfig } from "./constructor";

/**
 * Resolves a binding key to its display string, or `null` when it cannot be
 * resolved. Two implementations exist — the editor's PreviewDataProvider (sample
 * values) and the preview's BindingResolver (real applicant values). `null` means
 * "no value": the caller must not render the field. A diploma never shows a
 * service placeholder (—, N/A, null, …), so there is no stand-in value.
 */
export type BindingResolveFn = (binding: string) => string | null;

/**
 * Assemble a composite (nomination block): the prefix followed by the resolvable
 * parts joined by ", ", in canonical order. Missing parts are dropped; if none
 * remain the whole block is `null` (not rendered). Never yields a placeholder.
 */
function resolveNominationBlock(
  config: TemplateFieldConfig,
  resolve: BindingResolveFn,
): string | null {
  const chosen = new Set(config.parts ?? []);
  const values = NOMINATION_PARTS.filter((part) => chosen.has(part.key))
    .map((part) => resolve(part.binding))
    .filter((value): value is string => value != null && value !== "");
  if (values.length === 0) {
    return null;
  }
  const body = values.join(", ");
  const prefix = (config.prefix ?? "").trim();
  return prefix ? `${prefix} ${body}` : body;
}

/**
 * The single rule for a field's on-screen text, or `null` when the field must not
 * render: a composite assembles from its parts, a data-bound field resolves via
 * the provider (unresolved → `null`), a free field shows its own text. Shared by
 * editor and preview.
 */
export function resolveFieldDisplay(
  field: TemplateField,
  resolve: BindingResolveFn,
): string | null {
  if (field.config?.parts) {
    return resolveNominationBlock(field.config, resolve);
  }
  if (field.binding) {
    return resolve(field.binding);
  }
  return field.value ?? "";
}

/** BindingResolver from a resolved binding→value map; missing/empty keys → null. */
export function createBindingResolver(bindings: Record<string, string>): BindingResolveFn {
  return (binding) => {
    const value = bindings[binding];
    return value !== undefined && value !== "" ? value : null;
  };
}
