import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { defaultContactsConfig } from "../lib/contacts";
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

  it("marks contacts done when team contacts or venue exist", () => {
    const competition = baseCompetition({
      venue: { name: "Grand Hall", address: null },
      contactsConfig: {
        ...defaultContactsConfig(),
        teamContacts: [
          {
            id: "11111111-1111-7111-8111-111111111111",
            name: "Anna",
            position: "Coordinator",
            phone: null,
            email: "a@b.c",
            description: null,
            sortOrder: 0,
          },
        ],
      },
    });
    const checklist = buildPublicationChecklist(competition);
    const readiness = buildCompetitionReadiness(competition, checklist);
    expect(readiness.items.find((item) => item.sectionId === "contacts")?.done).toBe(true);
  });

  it("handles nullable landing lists for jury/partners/faq without crashing", () => {
    const competition = baseCompetition({
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
            id: "01900000-0000-7000-8000-000000000003",
            type: "JURY",
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
            id: "01900000-0000-7000-8000-000000000004",
            type: "PARTNERS",
            enabled: true,
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
            id: "01900000-0000-7000-8000-000000000006",
            type: "FAQ",
            enabled: true,
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
        ],
      },
    });
    const checklist = buildPublicationChecklist(competition);
    const readiness = buildCompetitionReadiness(competition, checklist);
    expect(readiness.items.find((item) => item.sectionId === "public-information")?.done).toBe(
      false,
    );
  });
});
