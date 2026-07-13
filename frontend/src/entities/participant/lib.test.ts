import { describe, expect, it } from "vitest";

import { toAddParticipantRequest } from "./lib";
import type { Participant } from "./model";

function participant(overrides: Partial<Participant>): Participant {
  return {
    id: "01900000-0000-7000-8000-000000000001",
    participantType: "solo",
    collectiveName: null,
    fullName: "Иванова Софья",
    firstName: "Софья",
    lastName: "Иванова",
    middleName: "Петровна",
    birthDate: "2013-03-04",
    age: 12,
    gender: "female",
    avatarUrl: null,
    notes: "",
    archived: false,
    applicationsCount: 0,
    primaryOrganization: null,
    organizations: [],
    updatedAt: "2026-07-12T00:00:00Z",
    ...overrides,
  };
}

describe("toAddParticipantRequest", () => {
  it("maps a solo participant to a full snapshot linked by registry id", () => {
    const request = toAddParticipantRequest(participant({}));
    expect(request).toEqual({
      participantRegistryId: "01900000-0000-7000-8000-000000000001",
      displayName: "Иванова Софья",
      firstName: "Софья",
      lastName: "Иванова",
      middleName: "Петровна",
      birthDate: "2013-03-04",
      gender: "FEMALE",
    });
  });

  it("uppercases each gender, including 'other'", () => {
    expect(toAddParticipantRequest(participant({ gender: "male" })).gender).toBe("MALE");
    expect(toAddParticipantRequest(participant({ gender: "other" })).gender).toBe("OTHER");
  });

  it("maps a collective to only the registry link and display name", () => {
    const request = toAddParticipantRequest(
      participant({
        participantType: "collective",
        collectiveName: 'Ensemble "Constellation"',
        fullName: 'Ensemble "Constellation"',
      }),
    );
    expect(request).toEqual({
      participantRegistryId: "01900000-0000-7000-8000-000000000001",
      displayName: 'Ensemble "Constellation"',
    });
    expect(request.birthDate).toBeUndefined();
    expect(request.gender).toBeUndefined();
  });
});
