import { describe, expect, it } from "vitest";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  buildAdditionalServiceReorderUpdates,
  buildAdditionalServicesStats,
  buildAdditionalServiceWarnings,
  createAdditionalServicePayload,
  emptyAdditionalServiceForm,
  filterAdditionalServices,
  nextAdditionalServiceSortOrder,
  sortAdditionalServices,
  validateAdditionalServiceForm,
} from "./additional-services";
import { defaultContactsConfig } from "./contacts";

function service(
  partial: Partial<CompetitionDetail["additionalServices"][number]> & { id: string; name: string },
): CompetitionDetail["additionalServices"][number] {
  return {
    amount: "50.00",
    currency: "BYN",
    description: null,
    billingModel: "PER_PARTICIPANT",
    participationFormatIds: ["fmt-1"],
    required: false,
    enabled: true,
    sortOrder: 0,
    ...partial,
  };
}

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
      allowApplicationEditing: true,
      allowWithdrawingApplications: false,
      requireTeacher: false,
      requireParentGuardian: false,
      participantCommentEnabled: false,
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
      formatRequirements: [],
    },
    deadlines: {
      application: null,
      payment: null,
      musicUpload: null,
      documentUpload: null,
      correction: null,
    },
    categories: [],
    disciplines: [],
    ageCategories: [],
    participantGroups: [],
    participationFormats: [
      {
        id: "fmt-1",
        name: "Очно",
        description: null,
        enabled: true,
        sortOrder: 0,
      },
      {
        id: "fmt-2",
        name: "Онлайн",
        description: null,
        enabled: false,
        sortOrder: 1,
      },
    ],
    admissionRules: [],
    pricingRules: [],
    regulations: [],
    currentRegulationId: null,
    documents: [],
    additionalServices: [
      service({ id: "s1", name: "Medal", sortOrder: 1, participationFormatIds: ["fmt-1"] }),
      service({
        id: "s2",
        name: "Shipping",
        sortOrder: 0,
        billingModel: "PER_PERFORMANCE",
        participationFormatIds: ["fmt-2"],
        required: true,
      }),
    ],
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

describe("additional services helpers", () => {
  it("sorts by sortOrder then name", () => {
    const sorted = sortAdditionalServices(competition().additionalServices);
    expect(sorted.map((item) => item.id)).toEqual(["s2", "s1"]);
  });

  it("filters by format name and billing label", () => {
    const detail = competition();
    expect(
      filterAdditionalServices(detail.additionalServices, "онлайн", detail.participationFormats),
    ).toHaveLength(1);
    expect(
      filterAdditionalServices(detail.additionalServices, "за номер", detail.participationFormats),
    ).toHaveLength(1);
  });

  it("validates required fields and builds payloads", () => {
    expect(validateAdditionalServiceForm(emptyAdditionalServiceForm())).toMatchObject({
      name: "Обязательное поле",
      amount: "Введите цену больше нуля",
      participationFormatIds: "Выберите хотя бы один формат участия",
    });

    const payload = createAdditionalServicePayload(
      {
        name: " Medal ",
        description: "  ",
        amount: "25,5",
        currency: "BYN",
        billingModel: "PER_PERFORMANCE",
        participationFormatIds: ["fmt-1"],
        required: true,
        enabled: true,
      },
      3,
    );
    expect(payload).toEqual({
      name: "Medal",
      amount: "25.50",
      currency: "BYN",
      description: null,
      billingModel: "PER_PERFORMANCE",
      participationFormatIds: ["fmt-1"],
      required: true,
      enabled: true,
      sortOrder: 3,
    });
    expect(nextAdditionalServiceSortOrder(competition().additionalServices)).toBe(2);
  });

  it("builds reorder updates only for changed sort orders", () => {
    const items = competition().additionalServices;
    const updates = buildAdditionalServiceReorderUpdates(["s1", "s2"], items);
    expect(updates).toHaveLength(2);
    expect(updates[0]?.payload.sortOrder).toBe(0);
    expect(updates[1]?.payload.sortOrder).toBe(1);
  });

  it("computes stats and warnings for disabled formats", () => {
    const detail = competition();
    const stats = buildAdditionalServicesStats(detail.additionalServices);
    expect(stats).toEqual({
      total: 2,
      enabledCount: 2,
      requiredCount: 1,
      perParticipantCount: 1,
      perPerformanceCount: 1,
    });
    const warnings = buildAdditionalServiceWarnings(detail);
    expect(warnings.some((item) => item.kind === "disabled-format")).toBe(true);
  });
});
