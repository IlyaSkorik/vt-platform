import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { admissionRuleKey } from "./admission-rules";
import { defaultContactsConfig } from "./contacts";
import {
  applyBulkOperation,
  buildPricingRows,
  buildPricingStats,
  buildPricingWarnings,
  filterPricingRows,
  parseAmount,
  planBulkPricingMutations,
  planCopyPricing,
} from "./pricing";

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
      { id: "d2", categoryId: "cat-2", name: "Pop", sortOrder: 0 },
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
        participantGroupId: "g1",
        name: "10–12",
        minAge: 10,
        maxAge: 12,
        sortOrder: 1,
        type: "STANDARD",
        mixedCalculationMethod: null,
      },
      {
        id: "a3",
        participantGroupId: "g3",
        name: "7–9",
        minAge: 7,
        maxAge: 9,
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
      {
        id: "g2",
        name: "Duet",
        minCount: 2,
        maxCount: 2,
        description: null,
        sortOrder: 1,
      },
      {
        id: "g3",
        name: "Solo",
        minCount: 1,
        maxCount: 1,
        description: null,
        sortOrder: 0,
      },
    ],
    participationFormats: [
      { id: "f1", name: "In Person", description: null, enabled: true, sortOrder: 0 },
      { id: "f2", name: "Online", description: null, enabled: true, sortOrder: 1 },
      { id: "f3", name: "Video", description: null, enabled: false, sortOrder: 2 },
    ],
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
        disciplineId: "d1",
        ageCategoryId: "a1",
        participantGroupId: "g1",
        participationFormatId: "f2",
      },
      {
        categoryId: "cat-1",
        disciplineId: "d1",
        ageCategoryId: "a2",
        participantGroupId: "g1",
        participationFormatId: "f1",
      },
      {
        categoryId: "cat-2",
        disciplineId: "d2",
        ageCategoryId: "a3",
        participantGroupId: "g3",
        participationFormatId: "f1",
      },
    ],
    pricingRules: [
      {
        categoryId: "cat-1",
        disciplineId: "d1",
        ageCategoryId: "a1",
        participantGroupId: "g1",
        participationFormatId: "f1",
        amount: "50.00",
        currency: "BYN",
        calculationType: "PER_PARTICIPANT",
      },
    ],
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

describe("pricing helpers", () => {
  it("parses and rejects non-positive amounts", () => {
    expect(parseAmount("50")).toBe(50);
    expect(parseAmount("50,5")).toBe(50.5);
    expect(parseAmount("0")).toBeNull();
    expect(parseAmount("-1")).toBeNull();
    expect(parseAmount("abc")).toBeNull();
  });

  it("builds rows highlighting missing prices", () => {
    const rows = buildPricingRows(competition());
    expect(rows).toHaveLength(4);
    expect(rows.filter((row) => row.status === "missing")).toHaveLength(3);
    expect(rows.filter((row) => row.status === "configured")).toHaveLength(1);
  });

  it("filters by missing price and search", () => {
    const rows = buildPricingRows(competition());
    expect(
      filterPricingRows(
        rows,
        {
          categoryId: null,
          disciplineId: null,
          ageCategoryId: null,
          participantGroupId: null,
          participationFormatId: null,
          priceStatus: "missing",
        },
        "",
      ),
    ).toHaveLength(3);
    expect(
      filterPricingRows(
        rows,
        {
          categoryId: null,
          disciplineId: null,
          ageCategoryId: null,
          participantGroupId: null,
          participationFormatId: null,
          priceStatus: null,
        },
        "online",
      ),
    ).toHaveLength(1);
  });

  it("plans bulk set and percent increase", () => {
    const detail = competition();
    const rows = buildPricingRows(detail);
    const first = rows[0];
    expect(first).toBeDefined();
    if (!first) return;
    const key = admissionRuleKey(first.rule);
    const setPlan = planBulkPricingMutations(rows, new Set([key]), { type: "set", amount: 40 });
    expect(setPlan.upserts[0]?.amount).toBe("40.00");
    expect(applyBulkOperation(50, { type: "increase-percent", percent: 10 })).toBe(55);
    expect(applyBulkOperation(50, { type: "decrease-amount", amount: 5 })).toBe(45);
  });

  it("plans bulk calculation type change only for priced rules that differ", () => {
    const detail = competition();
    const rows = buildPricingRows(detail);
    const priced = rows.find((row) => row.price);
    const missing = rows.find((row) => !row.price);
    expect(priced).toBeDefined();
    expect(missing).toBeDefined();
    if (!priced || !missing) return;

    const plan = planBulkPricingMutations(rows, new Set([priced.key, missing.key]), {
      type: "set-calculation-type",
      calculationType: "PER_PERFORMANCE",
    });
    expect(plan.upserts).toHaveLength(1);
    expect(plan.upserts[0]?.calculationType).toBe("PER_PERFORMANCE");
    expect(plan.upserts[0]?.amount).toBe("50.00");
    expect(plan.removes).toHaveLength(0);

    const noop = planBulkPricingMutations(rows, new Set([priced.key]), {
      type: "set-calculation-type",
      calculationType: "PER_PARTICIPANT",
    });
    expect(noop.upserts).toHaveLength(0);
  });

  it("copies prices between formats", () => {
    const plan = planCopyPricing(competition(), "format", "f1", "f2");
    expect(plan.items).toHaveLength(1);
    expect(plan.items[0]?.target.participationFormatId).toBe("f2");
    expect(plan.items[0]?.amount).toBe("50.00");
    expect(plan.items[0]?.calculationType).toBe("PER_PARTICIPANT");
    expect(plan.items[0]?.hadPrice).toBe(false);
  });

  it("copies prices between nominations by matching names", () => {
    const plan = planCopyPricing(competition(), "nomination", "cat-1", "cat-2");
    expect(plan.items).toHaveLength(1);
    expect(plan.items[0]?.target.categoryId).toBe("cat-2");
    expect(plan.items[0]?.target.disciplineId).toBe("d2");
  });

  it("computes stats and warnings", () => {
    const detail = competition({
      pricingRules: [
        ...competition().pricingRules,
        {
          categoryId: "cat-1",
          disciplineId: "d1",
          ageCategoryId: "a1",
          participantGroupId: "g1",
          participationFormatId: "f3",
          amount: "10.00",
          currency: "BYN",
          calculationType: "PER_PERFORMANCE",
        },
      ],
    });
    const stats = buildPricingStats(detail);
    expect(stats.missingPrices).toBe(3);
    expect(stats.configuredPrices).toBe(1);
    const warnings = buildPricingWarnings(detail);
    expect(warnings.some((item) => item.kind === "missing-price")).toBe(true);
    expect(warnings.some((item) => item.kind === "disabled-format-price")).toBe(true);
  });
});
