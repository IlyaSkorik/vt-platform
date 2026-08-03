import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  buildContactsSummary,
  createTeamContactDraft,
  defaultContactsConfig,
  moveTeamContactBefore,
  sortTeamContacts,
} from "./contacts";

function baseCompetition(overrides: Partial<CompetitionDetail> = {}): CompetitionDetail {
  return {
    id: "comp-1",
    title: "Spring Festival",
    season: "2025/2026",
    status: "DRAFT",
    organizerId: "org-1",
    description: null,
    branding: { logo: null, banner: null, poster: null },
    venue: null,
    registrationPeriod: null,
    competitionPeriod: null,
    settings: {
      allowMultipleApplications: false,
      allowApplicationEditing: true,
      allowWithdrawingApplications: true,
      requireTeacher: false,
      requireParentGuardian: false,
      participantCommentEnabled: false,
      requireDocumentUpload: false,
      allowAdditionalDocumentsLater: true,
      allowReplacingDocuments: true,
      paymentRequired: false,
      paymentTiming: "BEFORE_APPROVAL",
      paymentMethods: [],
      additionalPerformanceDiscountPercent: 0,
      requirePersonalDataConsent: true,
      requireMediaConsent: false,
      requireRegulationsAcceptance: true,
      manualApplicationApproval: true,
      automaticApprovalAfterPayment: false,
      allowReturningForCorrection: true,
      formatRequirements: [],
    },
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

describe("contacts helpers", () => {
  it("defaults to organization contacts inheritance", () => {
    expect(defaultContactsConfig().useOrganizationContacts).toBe(true);
    expect(defaultContactsConfig().teamContacts).toEqual([]);
  });

  it("reorders team contacts by drag target", () => {
    const a = {
      ...createTeamContactDraft(0),
      id: "11111111-1111-7111-8111-111111111111",
      name: "A",
    };
    const b = {
      ...createTeamContactDraft(1),
      id: "22222222-2222-7222-8222-222222222222",
      name: "B",
    };
    const c = {
      ...createTeamContactDraft(2),
      id: "33333333-3333-7333-8333-333333333333",
      name: "C",
    };
    const next = moveTeamContactBefore([a, b, c], a.id, c.id);
    expect(sortTeamContacts(next).map((item) => item.name)).toEqual(["B", "A", "C"]);
  });

  it("builds summary flags from competition and config", () => {
    const config = defaultContactsConfig();
    config.teamContacts = [
      { ...createTeamContactDraft(0), id: "11111111-1111-7111-8111-111111111111", name: "Anna" },
    ];
    config.emergency.phone = "112";
    const summary = buildContactsSummary(
      baseCompetition({ venue: { name: "Hall", address: null } }),
      config,
      "Взлёт талантов",
    );
    expect(summary).toEqual({
      organizationProfile: true,
      competitionContacts: true,
      venue: true,
      emergency: true,
    });
  });
});
