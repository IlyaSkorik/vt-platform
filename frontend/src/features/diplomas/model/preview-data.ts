import { PARTICIPANT_DISPLAY_NAME, type TemplateFieldBinding } from "./binding";

/**
 * Which sample entry preview values represent — a solo participant or a
 * collective. The same field/binding must render correctly for both, so the
 * editor can flip this to verify one field covers both scenarios.
 */
export type PreviewMode = "individual" | "collective";

const PREVIEW_VALUES: Record<PreviewMode, Record<TemplateFieldBinding, string>> = {
  individual: {
    [PARTICIPANT_DISPLAY_NAME]: "Иванов Иван Иванович",
  },
  collective: {
    [PARTICIPANT_DISPLAY_NAME]: "Ансамбль «Созвездие»",
  },
};

/** Placeholder shown when a binding has no sample value yet. */
const UNBOUND_PREVIEW = "—";

/**
 * PreviewDataProvider (pure): resolve a binding to a sample display value for
 * the given mode. At generation time a real provider will replace this with
 * actual applicant data; the renderer never knows the difference.
 */
export function resolvePreviewValue(binding: TemplateFieldBinding, mode: PreviewMode): string {
  return PREVIEW_VALUES[mode][binding] ?? PREVIEW_VALUES.individual[binding] ?? UNBOUND_PREVIEW;
}
