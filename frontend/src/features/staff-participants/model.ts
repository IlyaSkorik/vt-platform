/**
 * Organizer **Participant Registry** domain types.
 *
 * This is the *organizer-side* registry: a read-only projection of the
 * participants who have taken part in the organization's competitions, derived
 * on the backend from confirmed applications. It is deliberately distinct from
 * `@/entities/participant` (the *applicant-owned*, editable registry) — the
 * organizer never creates, edits, imports or deletes participants here.
 */

export type ParticipantGender = "MALE" | "FEMALE" | "OTHER";
export type ParticipantType = "solo" | "collective";

/** An educational organization a participant applied under (name snapshot). */
export interface RegistryOrganization {
  id: string | null;
  name: string;
}

/** A teacher who prepared the participant, as recorded on a submission. */
export interface RegistryTeacher {
  name: string;
  role: string;
}

/** One submission the participant appears in, inside this organization. */
export interface RegistryApplication {
  submissionId: string;
  applicationId: string | null;
  competitionId: string;
  competition: string;
  status: string;
  performanceTitle: string | null;
  organization: string | null;
  teachers: RegistryTeacher[];
  submittedAt: string;
  updatedAt: string;
}

/** A competitive act (one per submission) the participant performed. */
export interface RegistryPerformance {
  submissionId: string;
  competitionId: string;
  competition: string;
  status: string;
  title: string;
  durationSeconds: number | null;
  nomination: string | null;
  discipline: string | null;
  ageCategory: string | null;
  participantGroup: string | null;
  participationFormat: string | null;
}

/** A file uploaded within one of the participant's submissions. */
export interface RegistryDocument {
  id: string;
  submissionId: string;
  competition: string;
  type: string;
  file: string;
  caption: string | null;
}

/** A single participation event in this organization's competitions. */
export interface RegistryHistoryEntry {
  submissionId: string;
  competitionId: string;
  competition: string;
  status: string;
  date: string;
}

/** An internal organizer note recorded against one of the submissions. */
export interface RegistryNote {
  submissionId: string;
  competition: string;
  text: string;
  createdAt: string | null;
}

/** A participant award (reserved — no source context yet, always empty today). */
export interface RegistryAward {
  title: string;
  competition: string;
  date: string | null;
}

/** The dense-list row: identity plus aggregate counts. */
export interface RegistryParticipant {
  key: string;
  participantType: ParticipantType;
  displayName: string;
  firstName: string | null;
  lastName: string | null;
  middleName: string | null;
  fullName: string;
  birthDate: string | null;
  age: number | null;
  gender: ParticipantGender | null;
  memberCount: number;
  primaryOrganization: RegistryOrganization | null;
  organizations: RegistryOrganization[];
  teachers: RegistryTeacher[];
  competitionsCount: number;
  applicationsCount: number;
  performancesCount: number;
  documentsCount: number;
  lastActivity: string;
}

/** The full participant card. */
export interface RegistryParticipantDetail extends RegistryParticipant {
  applications: RegistryApplication[];
  performances: RegistryPerformance[];
  documents: RegistryDocument[];
  history: RegistryHistoryEntry[];
  notes: RegistryNote[];
  awards: RegistryAward[];
}

/** Server-computed quick-filter counts over the competition scope. */
export interface RegistryFacets {
  total: number;
  solo: number;
  collective: number;
  withDocuments: number;
  female: number;
  male: number;
}

/** A competition option for the filter dropdown. */
export interface RegistryCompetitionOption {
  id: string;
  title: string;
}

/** A page of registry rows plus the server-computed count, facets and filters. */
export interface RegistryList {
  rows: RegistryParticipant[];
  total: number;
  facets: RegistryFacets;
  competitions: RegistryCompetitionOption[];
}

/** Filters accepted by the list/export endpoints (all optional). */
export interface RegistryFilters {
  q?: string;
  gender?: string;
  ageMin?: string;
  ageMax?: string;
  competitionId?: string;
  organization?: string;
  participantType?: string;
  hasDocuments?: boolean;
}

/** Human-readable Russian labels for gender values (backend sends uppercase). */
export const GENDER_LABELS: Record<ParticipantGender, string> = {
  FEMALE: "Женский",
  MALE: "Мужской",
  OTHER: "Другой",
};

/** Safe gender label: tolerant of case/null/unknown, always returns a dash fallback. */
export function genderLabel(gender: string | null | undefined): string {
  if (gender == null || gender.length === 0) {
    return "—";
  }
  return GENDER_LABELS[gender.toUpperCase() as ParticipantGender] ?? "—";
}

/** Human-readable Russian labels for submission statuses shown in the card. */
export const SUBMISSION_STATUS_LABELS: Record<string, string> = {
  ACCEPTED: "Подтверждена",
  PAID: "Оплачена",
  SCHEDULED: "В расписании",
  COMPLETED: "Завершена",
};

/** Document type labels (mirrors the applications attachment taxonomy). */
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  MUSIC: "Музыка",
  VIDEO: "Видео",
  IMAGE: "Изображение",
  DOCUMENT: "Документ",
};

/** Two-letter initials for the avatar fallback. */
export function initialsFromName(fullName: string): string {
  return fullName
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Localized long date, tolerant of empty/invalid input. */
export function formatDate(value: string | null): string {
  if (value == null || value.length === 0) {
    return "—";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("ru-RU", { day: "2-digit", month: "long", year: "numeric" });
}

/** Grammatically-agnostic age suffix ("лет") — good enough for a dense table. */
export function formatAge(age: number | null): string {
  return age == null ? "—" : `${age} лет`;
}
