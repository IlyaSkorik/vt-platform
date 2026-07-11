import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { buildPublicationChecklist } from "./publication-checklist";

function baseCompetition(overrides: Partial<CompetitionDetail> = {}): CompetitionDetail {
  return {
    id: "comp-1",
    title: "Spring Festival",
    season: "2025/2026",
    status: "DRAFT",
    organizerId: "org-1",
    description: "A showcase",
    branding: { logo: null, banner: null, poster: null },
    venue: { name: "Hall", address: "Street 1" },
    registrationPeriod: { start: "2026-03-01", end: "2026-04-01" },
    competitionPeriod: { start: "2026-05-10", end: "2026-05-12" },
    settings: {
      allowMultipleApplications: false,
      allowApplicationEditing: true,
      allowMusicReplacement: true,
      allowVideoReplacement: true,
      allowParticipantChanges: true,
      requireMusicUpload: false,
      requireVideoUpload: false,
      requirePhotoUpload: false,
      requireIdentityDocument: false,
      requireParentConsent: false,
      requireTeacher: false,
      requireCommentForApplication: false,
    },
    deadlines: {
      application: null,
      payment: null,
      musicUpload: null,
      documentUpload: null,
      correction: null,
    },
    enabledFormats: [],
    categories: [],
    disciplines: [],
    ageCategories: [],
    participantGroups: [],
    admissionRules: [],
    pricingRules: [],
    regulations: [],
    currentRegulationId: null,
    documents: [],
    additionalServices: [],
    contacts: [],
    informationBlocks: [],
    createdAt: "2026-01-01T10:00:00.000Z",
    updatedAt: "2026-01-10T12:00:00.000Z",
    version: 1,
    ...overrides,
  };
}

describe("buildPublicationChecklist", () => {
  it("marks general complete when core fields are filled", () => {
    const checklist = buildPublicationChecklist(baseCompetition());
    expect(checklist.generalComplete).toBe(true);
    expect(checklist.isPublishable).toBe(false);
    expect(checklist.blockingIncomplete).toBeGreaterThan(0);
  });

  it("is publishable when taxonomy requirements are met", () => {
    const checklist = buildPublicationChecklist(
      baseCompetition({
        categories: [{ id: "c1", name: "Dance" }],
        disciplines: [{ id: "d1", categoryId: "c1", name: "Ballet" }],
        ageCategories: [{ id: "a1", minAge: 5, maxAge: 12 }],
        participantGroups: [{ id: "g1", categoryId: "c1", name: "Solo", minCount: 1, maxCount: 1 }],
        enabledFormats: ["SOLO"],
        admissionRules: [
          {
            categoryId: "c1",
            disciplineId: "d1",
            ageCategoryId: "a1",
            participantGroupId: "g1",
            participationFormat: "SOLO",
          },
        ],
        pricingRules: [
          {
            categoryId: "c1",
            disciplineId: "d1",
            ageCategoryId: "a1",
            participantGroupId: "g1",
            participationFormat: "SOLO",
            amount: "1000.00",
            currency: "RUB",
          },
        ],
        regulations: [
          {
            id: "reg-1",
            title: "Rules",
            version: "1.0",
            publicationDate: "2026-01-01",
            fileReference: "s3://r.pdf",
            isCurrent: true,
          },
        ],
        currentRegulationId: "reg-1",
      }),
    );

    expect(checklist.isPublishable).toBe(true);
    expect(checklist.blockingIncomplete).toBe(0);
  });
});
