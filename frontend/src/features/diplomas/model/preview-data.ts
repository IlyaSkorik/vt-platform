import {
  AWARD_DEGREE,
  COMPETITION_CITY,
  COMPETITION_DATE,
  COMPETITION_TITLE,
  DIPLOMA_ISSUE_DATE,
  DIPLOMA_NUMBER,
  NOMINATION_AGE_CATEGORY,
  NOMINATION_DISCIPLINE,
  NOMINATION_PARTICIPANT_GROUP,
  NOMINATION_TITLE,
  ORGANIZATION_NAME,
  PARTICIPANT_AGE,
  PARTICIPANT_DISPLAY_NAME,
  PERFORMANCE_TITLE,
  TEACHER_DISPLAY_NAME,
  type TemplateFieldBinding,
} from "./binding";

/**
 * Which sample entry preview values represent — a solo participant or a
 * collective. The same field/binding must render correctly for both, so the
 * editor can flip this to verify one field covers both scenarios.
 */
export type PreviewMode = "individual" | "collective";

/** Sample values shared by both modes (everything but the performer identity). */
const SHARED_VALUES: Record<TemplateFieldBinding, string> = {
  [TEACHER_DISPLAY_NAME]: "Педагог: Петрова Мария Сергеевна",
  [ORGANIZATION_NAME]: "ДШИ №1",
  [NOMINATION_TITLE]: "Вокал",
  [NOMINATION_DISCIPLINE]: "Эстрадный вокал",
  [NOMINATION_PARTICIPANT_GROUP]: "Соло",
  [NOMINATION_AGE_CATEGORY]: "10–12 лет",
  [PERFORMANCE_TITLE]: "«Этюд»",
  [COMPETITION_TITLE]: "Восходящие таланты",
  [COMPETITION_DATE]: "15.05.2026",
  [COMPETITION_CITY]: "Москва",
  [AWARD_DEGREE]: "Лауреат I степени",
  // Bare number — the QR block's caption adds the "№" itself.
  [DIPLOMA_NUMBER]: "VT-2026-000123",
  [DIPLOMA_ISSUE_DATE]: "20.05.2026",
};

const PREVIEW_VALUES: Record<PreviewMode, Record<TemplateFieldBinding, string>> = {
  individual: {
    ...SHARED_VALUES,
    [PARTICIPANT_DISPLAY_NAME]: "Иванов Иван Иванович",
    [PARTICIPANT_AGE]: "11",
  },
  collective: {
    ...SHARED_VALUES,
    [PARTICIPANT_DISPLAY_NAME]: "Ансамбль «Созвездие»",
    [PARTICIPANT_AGE]: "",
    [NOMINATION_PARTICIPANT_GROUP]: "Ансамбль",
  },
};

/**
 * PreviewDataProvider (pure): resolve a binding to a sample display value for the
 * given mode, or `null` when there is no sample (so the field is not rendered —
 * a diploma never shows a placeholder). At generation time a real provider
 * replaces this with actual applicant data; the renderer never knows the
 * difference.
 */
export function resolvePreviewValue(
  binding: TemplateFieldBinding,
  mode: PreviewMode,
): string | null {
  const value = PREVIEW_VALUES[mode][binding] ?? PREVIEW_VALUES.individual[binding];
  return value ? value : null;
}
