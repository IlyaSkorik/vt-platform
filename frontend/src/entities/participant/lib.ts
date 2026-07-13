/**
 * Mapping from a Participant Registry entry to the wizard's submission
 * add-participant request. The submission links back to the registry by id and
 * stores a display snapshot; a solo carries structured name/birth-date/gender, a
 * collective carries only its display name.
 */

import type {
  AddParticipantRequest,
  AddParticipantRequestGenderEnum,
} from "@/shared/api/generated/model-applications";

import { isCollective, type Participant, participantDisplayName } from "./model";

const GENDER_MAP: Record<Participant["gender"], AddParticipantRequestGenderEnum> = {
  female: "FEMALE",
  male: "MALE",
  other: "OTHER",
};

/**
 * Build the add-participant request for a chosen registry participant. Solo
 * participants contribute their full structured snapshot and count as one person;
 * a collective contributes only a display name plus its headcount (`memberCount`),
 * which drives the count-band check and per-participant pricing.
 */
export function toAddParticipantRequest(
  participant: Participant,
  memberCount?: number,
): AddParticipantRequest {
  if (isCollective(participant)) {
    return {
      participantRegistryId: participant.id,
      displayName: participantDisplayName(participant),
      memberCount: memberCount && memberCount > 0 ? memberCount : 1,
    };
  }
  return {
    participantRegistryId: participant.id,
    displayName: participantDisplayName(participant),
    firstName: participant.firstName,
    lastName: participant.lastName,
    middleName: participant.middleName,
    birthDate: participant.birthDate,
    gender: GENDER_MAP[participant.gender],
  };
}
