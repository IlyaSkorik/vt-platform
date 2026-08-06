import { describe, expect, it } from "vitest";
import {
  ACCOUNT_CONSENTS,
  APPLICATION_CONSENTS,
  applicationConsent,
  type ConsentDefinition,
  PARTICIPANT_CONSENT,
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
  TEACHER_CONSENT,
  ...Object.values(APPLICATION_CONSENTS),
];

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
});
