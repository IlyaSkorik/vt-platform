import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { buildCompetitionReadiness } from "./competition-readiness";
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
      allowWithdrawingApplications: false,
      allowCopyingPreviousApplications: false,
      requireTeacher: false,
      requireParentGuardian: false,
      participantCommentEnabled: false,
      requireDocumentUpload: false,
      allowAdditionalDocumentsLater: true,
      allowReplacingDocuments: true,
      paymentRequired: false,
      paymentTiming: "BEFORE_APPROVAL" as const,
      paymentMethods: ["BANK_TRANSFER" as const],
      requirePersonalDataConsent: true,
      requireMediaConsent: false,
      requireRegulationsAcceptance: true,
      emailNotifications: true,
      cabinetNotifications: true,
      smsNotifications: false,
      pushNotifications: false,
      manualApplicationApproval: false,
      automaticApprovalAfterPayment: false,
      allowReturningForCorrection: false,
      formatRequirements: [],
    },
    deadlines: {
      application: null,
      payment: null,
      musicUpload: null,
      documentUpload: null,
      correction: null,
    },
    participationFormats: [],
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

describe("buildCompetitionReadiness", () => {
  it("lists every workspace section and marks contacts incomplete when empty", () => {
    const competition = baseCompetition();
    const checklist = buildPublicationChecklist(competition);
    const readiness = buildCompetitionReadiness(competition, checklist);

    expect(readiness.items.some((item) => item.sectionId === "settings")).toBe(true);
    expect(readiness.items.find((item) => item.sectionId === "settings")?.label).toBe(
      "Правила участия",
    );
    expect(readiness.items.find((item) => item.sectionId === "contacts")?.done).toBe(false);
    expect(readiness.items.find((item) => item.sectionId === "settings")?.done).toBe(true);
    expect(readiness.percent).toBeGreaterThanOrEqual(0);
    expect(readiness.incomplete).toBeGreaterThan(0);
  });

  it("marks contacts done when present", () => {
    const competition = baseCompetition({
      contacts: [
        {
          id: "c1",
          type: "email",
          value: "a@b.c",
          isPrimary: true,
        },
      ],
    });
    const checklist = buildPublicationChecklist(competition);
    const readiness = buildCompetitionReadiness(competition, checklist);
    expect(readiness.items.find((item) => item.sectionId === "contacts")?.done).toBe(true);
  });
});
