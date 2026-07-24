import { NOMINATION_PARTS, type TemplateField, type TemplateFieldConfig } from "./constructor";

/**
 * Resolves a binding key to a display string. Two implementations exist — the
 * editor's PreviewDataProvider (sample values) and the preview's BindingResolver
 * (real applicant values) — and the renderer works with either, unchanged.
 */
export type BindingResolveFn = (binding: string) => string;

/**
 * What a binding with no value renders as: nothing (an empty string). An unfilled
 * field shows no placeholder dash; the UI still never crashes on a gap.
 */
export const MISSING_VALUE = "";

/**
 * Assemble a composite (nomination block) into one string: the prefix followed
 * by the chosen parts joined by ", ", in canonical order. Missing/empty parts are
 * dropped so a gap never leaves a stray "—" or comma. With nothing resolved the
 * whole block is the placeholder.
 */
function resolveNominationBlock(config: TemplateFieldConfig, resolve: BindingResolveFn): string {
  const chosen = new Set(config.parts ?? []);
  const values = NOMINATION_PARTS.filter((part) => chosen.has(part.key))
    .map((part) => resolve(part.binding))
    .filter((value) => value && value !== MISSING_VALUE);
  const body = values.join(", ");
  if (!body) {
    return MISSING_VALUE;
  }
  const prefix = (config.prefix ?? "").trim();
  return prefix ? `${prefix} ${body}` : body;
}

/**
 * The single rule for a field's on-screen text: a composite field assembles from
 * its parts, a data-bound field resolves via the provider, a free field shows its
 * own value. Shared by editor and preview.
 */
export function resolveFieldDisplay(field: TemplateField, resolve: BindingResolveFn): string {
  if (field.config?.parts) {
    return resolveNominationBlock(field.config, resolve);
  }
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
