import { describe, expect, it } from "vitest";
import {
  ACCOUNT_CONSENTS,
  ADULT_PARTICIPANT_CONSENT,
  APPLICATION_CONSENTS,
  applicationConsent,
  type ConsentDefinition,
  PARTICIPANT_CONSENT,
  participantConsent,
  TEACHER_CONSENT,
} from "./index";

/**
 * These tests guard properties of the *texts*, not of the code that renders them.
 *
 * A consent is only valid if the person could tell what they were agreeing to, and the
 * platform can only prove what was agreed if the version travels with it. Both are
 * things a well-meaning edit can quietly break — shortening a text to a label,
 * reusing a version for new wording — so they are asserted rather than trusted.
 */

const ALL: readonly ConsentDefinition[] = [
  ...ACCOUNT_CONSENTS,
  PARTICIPANT_CONSENT,
  ADULT_PARTICIPANT_CONSENT,
  TEACHER_CONSENT,
  ...Object.values(APPLICATION_CONSENTS),
];

/** A birth date that lands the participant on exactly `age` on `TODAY`. */
const TODAY = new Date(2026, 7, 10);
function bornAged(age: number): string {
  return `${TODAY.getFullYear() - age}-01-15`;
}

describe("consent catalogue", () => {
  it("gives every consent a code and a version", () => {
    for (const consent of ALL) {
      expect(consent.code, JSON.stringify(consent)).toMatch(/^[a-z_]+$/);
      // 40 characters is the shortest limit any of the three backends imposes on a
      // stored version (the applications value object), so a version longer than that
      // would be recorded nowhere.
      expect(consent.version.length).toBeLessThanOrEqual(40);
    }
  });

  it("states what is being agreed to, not just its name", () => {
    for (const consent of ALL) {
      // A one-line label is a title, not information. The full text is what makes the
      // consent informed, so it has to say substantially more than the summary.
      expect(consent.summary.length, consent.code).toBeGreaterThan(40);
      expect(consent.text.length, consent.code).toBeGreaterThan(consent.summary.length);
    }
  });

  it("keeps the account codes distinct from one another", () => {
    const codes = ACCOUNT_CONSENTS.flatMap((consent) => consent.records ?? [consent.code]);
    expect(new Set(codes).size).toBe(codes.length);
  });

  it("asks for permission to process separately from accepting the terms", () => {
    const terms = ACCOUNT_CONSENTS.find((consent) => consent.code === "terms_of_service");
    const processing = ACCOUNT_CONSENTS.find((consent) => consent.code === "data_processing");
    expect(terms?.required).toBe(true);
    expect(processing?.required).toBe(true);
    // The terms box may stand for the policy acknowledgement, but never for the
    // processing consent — that one is its own decision.
    expect(terms?.records).not.toContain("data_processing");
  });

  it("leaves the newsletter optional", () => {
    expect(ACCOUNT_CONSENTS.find((consent) => consent.code === "marketing")?.required).toBe(false);
  });

  it("requires the consents a festival cannot waive, and only those", () => {
    // Mirrors the backend projection: processing a child's data and distributing the
    // results are always required; everything else is the organizer's or the
    // applicant's choice (LEGAL-001 §4.1, §8.3, §8.5).
    expect(applicationConsent("personal_data")?.required).toBe(true);
    expect(applicationConsent("distribution")?.required).toBe(true);
    expect(applicationConsent("media")?.required).toBe(false);
    expect(applicationConsent("regulations")?.required).toBe(false);
    expect(applicationConsent("work_publication")?.required).toBe(false);
  });

  it("has no wording for a code it does not know", () => {
    expect(applicationConsent("something_invented")).toBeUndefined();
  });

  it("confirms a teacher's consent rather than pretending to give it", () => {
    // Nobody can consent on behalf of an adult who is not in the room, so the wording
    // is a confirmation that their consent was already obtained (LEGAL-001 §5.4) — and
    // it must not be the code the account holder uses for their own data.
    expect(TEACHER_CONSENT.code).toBe("third_party_data_processing");
    expect(TEACHER_CONSENT.required).toBe(true);
    expect(TEACHER_CONSENT.summary).toMatch(/подтвержда/i);
    expect(ACCOUNT_CONSENTS.map((consent) => consent.code)).not.toContain(TEACHER_CONSENT.code);
    // And it tells the teacher how to take it back.
    expect(TEACHER_CONSENT.text).toMatch(/отозвать/i);
  });

  it("tells the participant consent apart from the account's own", () => {
    // The child's consent is granted by an adult about someone else, so it must not be
    // confusable with the adult consenting for themselves.
    expect(PARTICIPANT_CONSENT.code).toBe("minor_data_processing");
    expect(ACCOUNT_CONSENTS.map((consent) => consent.code)).not.toContain(PARTICIPANT_CONSENT.code);
    expect(PARTICIPANT_CONSENT.text).toMatch(/законн/i);
  });

  it("asks an adult participant for their own consent, not a representative's", () => {
    // Nobody represents an adult, so the wording that says "I am the legal
    // representative" must not be the one an eighteen-year-old's record rests on
    // (LEGAL-001 §6.2). It is the teacher pattern: a confirmation that the person's own
    // consent was obtained.
    const adult = participantConsent({ birthDate: bornAged(18), on: TODAY });
    expect(adult).toBe(ADULT_PARTICIPANT_CONSENT);
    expect(adult.code).toBe("third_party_data_processing");
    expect(adult.summary).toMatch(/подтвержда/i);
    expect(adult.text).not.toMatch(/законн(ый|ого) представител/i);
    expect(adult.text).toMatch(/изображени/i);
  });

  it("keeps a minor on the representative's consent right up to the birthday", () => {
    expect(participantConsent({ birthDate: bornAged(17), on: TODAY })).toBe(PARTICIPANT_CONSENT);
    // The day before turning eighteen is still the day of a child.
    expect(participantConsent({ birthDate: "2008-08-11", on: TODAY })).toBe(PARTICIPANT_CONSENT);
    expect(participantConsent({ birthDate: "2008-08-10", on: TODAY })).toBe(
      ADULT_PARTICIPANT_CONSENT,
    );
  });

  it("falls back to the stricter basis when age cannot be established", () => {
    // A collective is not a person and any of its members may be a child; a missing or
    // unreadable date must not be a way of selecting the weaker basis by omission.
    expect(
      participantConsent({ birthDate: bornAged(40), participantType: "collective", on: TODAY }),
    ).toBe(PARTICIPANT_CONSENT);
    expect(participantConsent({ birthDate: null, on: TODAY })).toBe(PARTICIPANT_CONSENT);
    expect(participantConsent({ birthDate: "", on: TODAY })).toBe(PARTICIPANT_CONSENT);
    expect(participantConsent({ birthDate: "not-a-date", on: TODAY })).toBe(PARTICIPANT_CONSENT);
  });

  it("names the participant's photograph among the data it covers", () => {
    // The registry stores an avatar for every participant it holds — see
    // `backend/apps/participants/presentation/api/v1/registry/avatars.py`, and
    // `avatar_url` on `ParticipantRegistryModel`. A category of data the consent does
    // not name is a category that may not be processed at all (art. 4 §5 and art. 5 of
    // Law 99-З), so the enumeration in the text has to keep pace with the columns.
    expect(PARTICIPANT_CONSENT.text).toMatch(/изображени/i);
  });
});
