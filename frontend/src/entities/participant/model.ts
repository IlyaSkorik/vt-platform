/**
 * Participant Registry domain model — the reusable, user-owned registry of
 * participants (solo people and collectives/ensembles) shared by the registry
 * pages and the Registration Wizard's participant picker. One canonical shape,
 * no per-feature duplication.
 */

export type Gender = "female" | "male" | "other";
export type ParticipantType = "solo" | "collective";
export type OrganizationType =
  | "school"
  | "music_school"
  | "dance_studio"
  | "art_school"
  | "college"
  | "university"
  | "cultural_center"
  | "creative_center"
  | "private_studio"
  | "other";

export interface Organization {
  id: string;
  name: string;
  type: OrganizationType;
  country: string | null;
  city: string | null;
  address: string | null;
  website: string | null;
  participantsCount?: number;
  isUsed?: boolean;
  archived?: boolean;
}

export interface ParticipantOrganization extends Organization {
  isPrimary: boolean;
}

export interface Participant {
  id: string;
  participantType: ParticipantType;
  collectiveName: string | null;
  fullName: string;
  firstName: string;
  lastName: string;
  middleName: string | null;
  birthDate: string;
  age: number;
  gender: Gender;
  avatarUrl: string | null;
  notes: string;
  archived: boolean;
  applicationsCount: number;
  primaryOrganization: Organization | null;
  organizations: ParticipantOrganization[];
  updatedAt: string;
}

/** Whether a registry entry is a collective/ensemble rather than a solo person. */
export function isCollective(participant: Participant): boolean {
  return participant.participantType === "collective";
}

/** The label shown for a participant (collective name, or the person's full name). */
export function participantDisplayName(participant: Participant): string {
  return (
    (isCollective(participant) ? participant.collectiveName : participant.fullName) ??
    participant.fullName
  );
}
