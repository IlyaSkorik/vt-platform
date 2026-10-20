import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  admissionRuleKey,
  buildAdmissionCoverageWarnings,
  buildAdmissionLookupMaps,
  cartesianCount,
  filterAdmissionRules,
  planBulkAdmissionRules,
  toggleId,
} from "./admission-rules";
import { defaultContactsConfig } from "./contacts";

function competition(partial: Partial<CompetitionDetail> = {}): CompetitionDetail {
  return {
    id: "c1",
    title: "Fest",
    season: "2025/2026",
    status: "DRAFT",
    organizerId: "o1",
    description: null,
    branding: { logo: null, banner: null, poster: null },
    venue: { name: "", address: null },
    registrationPeriod: { start: "", end: "" },
    competitionPeriod: { start: "", end: "" },
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
    editingLockedAt: null,
    categories: [
      {
        id: "cat-1",
        name: "Vocal",
        description: null,
        sortOrder: 0,
        registrationOpensAt: null,
        registrationClosesAt: null,
        registrationStopped: false,
        waitlistEnabled: false,
      },
      {
        id: "cat-2",
        name: "Dance",
        description: null,
        sortOrder: 1,
        registrationOpensAt: null,
        registrationClosesAt: null,
        registrationStopped: false,
        waitlistEnabled: false,
      },
    ],
    disciplines: [
      { id: "d1", categoryId: "cat-1", name: "Pop", sortOrder: 0 },
      { id: "d2", categoryId: "cat-1", name: "Jazz", sortOrder: 1 },
      { id: "d3", categoryId: "cat-2", name: "Ballet", sortOrder: 0 },
    ],
    ageCategories: [
      {
        id: "a1",
        participantGroupId: "g1",
        name: "7–9",
        minAge: 7,
        maxAge: 9,
        sortOrder: 0,
        type: "STANDARD",
        mixedCalculationMethod: null,
      },
      {
        id: "a2",
        participantGroupId: "g2",
        name: "10–12",
        minAge: 10,
        maxAge: 12,
        sortOrder: 1,
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
      {
        id: "g2",
        name: "Duet",
        minCount: 2,
        maxCount: 2,
        description: null,
        sortOrder: 1,
      },
    ],
    participationFormats: [
      { id: "f1", name: "Очно", description: null, enabled: true, sortOrder: 0 },
      { id: "f2", name: "Онлайн", description: null, enabled: true, sortOrder: 1 },
    ],
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
    createdAt: "2026-01-01T00:00:00.000Z",
    updatedAt: "2026-01-01T00:00:00.000Z",
    version: 1,
    ...partial,
  };
}

describe("admission rules helpers", () => {
  it("builds cartesian bulk plan and skips existing combinations", () => {
    const draft = {
      categoryId: "cat-1",
      disciplineIds: ["d1"],
      ageCategoryIds: ["a1", "a2"],
      participantGroupIds: ["g1", "g2"],
      participationFormatIds: ["f1", "f2"],
    };
    expect(cartesianCount(draft)).toBe(8);

    const existing = new Set([
      admissionRuleKey({
        categoryId: "cat-1",
        disciplineId: "d1",
        ageCategoryId: "a1",
        participantGroupId: "g1",
        participationFormatId: "f1",
      }),
    ]);
    const plan = planBulkAdmissionRules(draft, existing);
    expect(plan.totalRequested).toBe(8);
    expect(plan.skippedExisting).toBe(1);
    expect(plan.toCreate).toHaveLength(7);
  });

  it("filters rules by dimension and search labels", () => {
    const detail = competition({
      admissionRules: [
        {
          categoryId: "cat-1",
          disciplineId: "d1",
          ageCategoryId: "a1",
          participantGroupId: "g1",
          participationFormatId: "f1",
        },
        {
          categoryId: "cat-1",
          disciplineId: "d2",
          ageCategoryId: "a2",
          participantGroupId: "g2",
          participationFormatId: "f2",
        },
      ],
    });
    const maps = buildAdmissionLookupMaps(detail);
    expect(
      filterAdmissionRules(
        detail.admissionRules,
        {
          categoryId: null,
          disciplineId: "d1",
          ageCategoryId: null,
          participantGroupId: null,
          participationFormatId: null,
        },
        "",
        maps,
      ),
    ).toHaveLength(1);
    expect(
      filterAdmissionRules(
        detail.admissionRules,
        {
          categoryId: null,
          disciplineId: null,
          ageCategoryId: null,
          participantGroupId: null,
          participationFormatId: null,
        },
        "duet",
        maps,
      ),
    ).toHaveLength(1);
  });

  it("builds coverage warnings for unused taxonomy", () => {
    const warnings = buildAdmissionCoverageWarnings(
      competition({
        admissionRules: [
          {
            categoryId: "cat-1",
            disciplineId: "d1",
            ageCategoryId: "a1",
            participantGroupId: "g1",
            participationFormatId: "f1",
          },
        ],
      }),
    );
    expect(warnings.some((item) => item.kind === "nomination")).toBe(true);
    expect(warnings.some((item) => item.kind === "discipline")).toBe(true);
    expect(warnings.some((item) => item.kind === "participant-group")).toBe(true);
    expect(warnings.some((item) => item.kind === "format")).toBe(true);
  });

  it("toggles ids in multi-select lists", () => {
    expect(toggleId(["a"], "b")).toEqual(["a", "b"]);
    expect(toggleId(["a", "b"], "a")).toEqual(["b"]);
  });
});
