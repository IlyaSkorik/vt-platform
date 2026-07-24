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

// --- Binding Catalog (business keys) ---------------------------------------
// Adding a data field is three steps: a constant here, a value in the backend
// BindingResolver, and a palette entry. Nothing in the editor changes.

export const PARTICIPANT_DISPLAY_NAME: TemplateFieldBinding = "participant.display_name";
export const PARTICIPANT_AGE: TemplateFieldBinding = "participant.age";
export const TEACHER_DISPLAY_NAME: TemplateFieldBinding = "teacher.display_name";
export const ORGANIZATION_NAME: TemplateFieldBinding = "organization.name";
export const NOMINATION_TITLE: TemplateFieldBinding = "nomination.title";
export const NOMINATION_DISCIPLINE: TemplateFieldBinding = "nomination.discipline";
export const NOMINATION_PARTICIPANT_GROUP: TemplateFieldBinding = "nomination.participant_group";
export const NOMINATION_AGE_CATEGORY: TemplateFieldBinding = "nomination.age_category";
export const PERFORMANCE_TITLE: TemplateFieldBinding = "performance.title";
export const COMPETITION_TITLE: TemplateFieldBinding = "competition.title";
export const COMPETITION_DATE: TemplateFieldBinding = "competition.date";
export const COMPETITION_CITY: TemplateFieldBinding = "competition.city";
export const AWARD_DEGREE: TemplateFieldBinding = "award.degree";
export const AWARD_PLACE: TemplateFieldBinding = "award.place";
export const DIPLOMA_NUMBER: TemplateFieldBinding = "diploma.number";
export const DIPLOMA_ISSUE_DATE: TemplateFieldBinding = "diploma.issue_date";

export const KNOWN_BINDINGS = {
  participantDisplayName: PARTICIPANT_DISPLAY_NAME,
  participantAge: PARTICIPANT_AGE,
  teacherDisplayName: TEACHER_DISPLAY_NAME,
  organizationName: ORGANIZATION_NAME,
  nominationTitle: NOMINATION_TITLE,
  nominationDiscipline: NOMINATION_DISCIPLINE,
  nominationParticipantGroup: NOMINATION_PARTICIPANT_GROUP,
  nominationAgeCategory: NOMINATION_AGE_CATEGORY,
  performanceTitle: PERFORMANCE_TITLE,
  competitionTitle: COMPETITION_TITLE,
  competitionDate: COMPETITION_DATE,
  competitionCity: COMPETITION_CITY,
  awardDegree: AWARD_DEGREE,
  awardPlace: AWARD_PLACE,
  diplomaNumber: DIPLOMA_NUMBER,
  diplomaIssueDate: DIPLOMA_ISSUE_DATE,
} as const;

/**
 * The default data source for a field kind. This is the one seam a new data
 * field extends — add a `type → binding` entry and the editor needs no changes.
 * Types with no entry (`qr`, `free_text`) are not data-bound.
 */
const DEFAULT_BINDINGS: Partial<Record<TemplateFieldTypeId, TemplateFieldBinding>> = {
  participant_name: PARTICIPANT_DISPLAY_NAME,
  participant_age: PARTICIPANT_AGE,
  teacher: TEACHER_DISPLAY_NAME,
  organization: ORGANIZATION_NAME,
  nomination: NOMINATION_TITLE,
  discipline: NOMINATION_DISCIPLINE,
  participant_group: NOMINATION_PARTICIPANT_GROUP,
  age_category: NOMINATION_AGE_CATEGORY,
  work: PERFORMANCE_TITLE,
  competition_name: COMPETITION_TITLE,
  competition_date: COMPETITION_DATE,
  competition_city: COMPETITION_CITY,
  award_degree: AWARD_DEGREE,
  award_place: AWARD_PLACE,
  diploma_number: DIPLOMA_NUMBER,
  diploma_issue_date: DIPLOMA_ISSUE_DATE,
};

export function defaultBindingForType(type: TemplateFieldTypeId): TemplateFieldBinding {
  return DEFAULT_BINDINGS[type] ?? "";
}
