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
 * participants contribute their full structured snapshot; collectives contribute
 * only a display name (the registry link is authoritative for their members).
 */
export function toAddParticipantRequest(participant: Participant): AddParticipantRequest {
  const base: AddParticipantRequest = {
    participantRegistryId: participant.id,
    displayName: participantDisplayName(participant),
  };
  if (isCollective(participant)) {
    return base;
  }
  return {
    ...base,
    firstName: participant.firstName,
    lastName: participant.lastName,
    middleName: participant.middleName,
    birthDate: participant.birthDate,
    gender: GENDER_MAP[participant.gender],
  };
}
