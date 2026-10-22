import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { defaultContactsConfig } from "../lib/contacts";
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
      allowMultiplePerformances: true,
      allowApplicationEditing: true,
      allowWithdrawingApplications: false,
      requireTeacher: false,
      requireParentGuardian: false,
      participantCommentEnabled: false,
      collectPayerDetails: false,
      requireDocumentUpload: false,
      allowAdditionalDocumentsLater: true,
      allowReplacingDocuments: true,
      paymentRequired: false,
      paymentTiming: "BEFORE_APPROVAL" as const,
      paymentMethods: ["BANK_TRANSFER" as const],
      additionalPerformanceDiscountPercent: 0,
      autoCancelUnpaidApplications: true,
      requirePersonalDataConsent: true,
      requireMediaConsent: false,
      requireRegulationsAcceptance: true,
      manualApplicationApproval: false,
      automaticApprovalAfterPayment: false,
      allowReturningForCorrection: false,
      judgingMode: "PROTOCOLS",
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
    contactsConfig: defaultContactsConfig(),
    landingConfig: {
      blocks: [
        {
          id: "01900000-0000-7000-8000-000000000001",
          type: "HERO",
          enabled: true,
          sortOrder: 0,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          cards: [],
          partners: [],
          images: [],
          faqItems: [],
        },
        {
          id: "01900000-0000-7000-8000-000000000002",
          type: "VENUE",
          enabled: true,
          sortOrder: 1,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          cards: [],
          partners: [],
          images: [],
          faqItems: [],
        },
        {
          id: "01900000-0000-7000-8000-000000000003",
          type: "JURY",
          enabled: false,
          sortOrder: 2,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          cards: [],
          partners: [],
          images: [],
          faqItems: [],
        },
        {
          id: "01900000-0000-7000-8000-000000000004",
          type: "PARTNERS",
          enabled: false,
          sortOrder: 3,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          cards: [],
          partners: [],
          images: [],
          faqItems: [],
        },
        {
          id: "01900000-0000-7000-8000-000000000005",
          type: "GALLERY",
          enabled: false,
          sortOrder: 4,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          cards: [],
          partners: [],
          images: [],
          faqItems: [],
        },
        {
          id: "01900000-0000-7000-8000-000000000006",
          type: "FAQ",
          enabled: false,
          sortOrder: 5,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          cards: [],
          partners: [],
          images: [],
          faqItems: [],
        },
      ],
    },
    contacts: [],
    informationBlocks: [],
    createdAt: "2026-01-01T10:00:00.000Z",
    updatedAt: "2026-01-10T12:00:00.000Z",
    version: 1,
    ...overrides,
  };
}

/** A competition with everything publication requires, priced unless told otherwise. */
function configuredCompetition(overrides: Partial<CompetitionDetail> = {}): CompetitionDetail {
  return baseCompetition({
    categories: [
      {
        id: "c1",
        name: "Dance",
        description: null,
        sortOrder: 0,
        registrationOpensAt: null,
        registrationClosesAt: null,
        registrationStopped: false,
        waitlistEnabled: false,
        heldAt: null,
        editingLockedAt: null,
      },
    ],
    disciplines: [{ id: "d1", categoryId: "c1", name: "Ballet", sortOrder: 0 }],
    ageCategories: [
      {
        id: "a1",
        participantGroupId: "g1",
        name: "5–12 лет",
        minAge: 5,
        maxAge: 12,
        sortOrder: 0,
        type: "STANDARD",
        mixedCalculationMethod: null,
      },
    ],
    participantGroups: [
      {
        id: "g1",
        name: "Solo",
        minCount: 1,
        maxCount: 1,
        description: null,
        sortOrder: 0,
      },
    ],
    participationFormats: [
      {
        id: "f1",
        name: "Очно",
        description: null,
        enabled: true,
        sortOrder: 0,
      },
    ],
    admissionRules: [
      {
        categoryId: "c1",
        disciplineId: "d1",
        ageCategoryId: "a1",
        participantGroupId: "g1",
        participationFormatId: "f1",
      },
    ],
    pricingRules: [
      {
        categoryId: "c1",
        disciplineId: "d1",
        ageCategoryId: "a1",
        participantGroupId: "g1",
        participationFormatId: "f1",
        amount: "1000.00",
        currency: "RUB",
        calculationType: "PER_PARTICIPANT",
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
    ...overrides,
  });
}

describe("buildPublicationChecklist", () => {
  it("marks general complete when core fields are filled", () => {
    const checklist = buildPublicationChecklist(baseCompetition());
    expect(checklist.generalComplete).toBe(true);
    expect(checklist.isPublishable).toBe(false);
    expect(checklist.blockingIncomplete).toBeGreaterThan(0);
  });

  it("is publishable when taxonomy requirements are met", () => {
    const checklist = buildPublicationChecklist(configuredCompetition());

    expect(checklist.isPublishable).toBe(true);
    expect(checklist.blockingIncomplete).toBe(0);
  });

  it("is publishable without any prices — pricing is advisory", () => {
    const checklist = buildPublicationChecklist(configuredCompetition({ pricingRules: [] }));

    expect(checklist.isPublishable).toBe(true);
    expect(checklist.blockingIncomplete).toBe(0);
    expect(checklist.items.find((item) => item.id === "pricing")).toMatchObject({
      done: false,
      blocking: false,
    });
  });
});
