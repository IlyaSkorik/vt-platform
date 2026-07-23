import type { TemplateFieldTypeId } from "./constructor";

/**
 * A reference to the data that fills a field at generation time — not literal
 * text. Bindings are dotted business keys (`participant.display_name`), never
 * storage columns. `participant.display_name` is the field's single "display
 * name" of the performer: the individual's full name for a solo entry, or the
 * ensemble's name for a collective — the editor never distinguishes the two.
 *
 * Kept as a widened string so new sources add entries without a type change;
 * `KNOWN_BINDINGS` documents the ones in use.
 */
export type TemplateFieldBinding = string;

export const PARTICIPANT_DISPLAY_NAME: TemplateFieldBinding = "participant.display_name";

export const KNOWN_BINDINGS = {
  participantDisplayName: PARTICIPANT_DISPLAY_NAME,
} as const;

/**
 * The default data source for a field kind. This is the one seam future field
 * types extend — add a `type → binding` entry and the editor needs no changes.
 * Only `participant_name` is wired for now.
 */
const DEFAULT_BINDINGS: Partial<Record<TemplateFieldTypeId, TemplateFieldBinding>> = {
  participant_name: PARTICIPANT_DISPLAY_NAME,
};

export function defaultBindingForType(type: TemplateFieldTypeId): TemplateFieldBinding {
  return DEFAULT_BINDINGS[type] ?? "";
}
