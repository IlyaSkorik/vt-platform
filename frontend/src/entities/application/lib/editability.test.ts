import { describe, expect, it } from "vitest";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { canApplicantEditApplication } from "./editability";

function application(overrides: Partial<ApplicationResource> = {}): ApplicationResource {
  return {
    id: "01930000-0000-7000-8000-000000000001",
    competitionId: "01930000-0000-7000-8000-000000000002",
    applicantId: "01930000-0000-7000-8000-000000000003",
    status: "SUBMITTED",
    hasCorrections: false,
    correctionComment: null,
    educationalOrganizationId: null,
    organizationName: null,
    payer: null,
    submissions: [],
    services: [],
    consents: [],
    totalPrice: null,
    paymentReceipts: [],
    paidAt: null,
    createdAt: "2026-08-17T10:00:00.000Z",
    updatedAt: "2026-08-17T10:00:00.000Z",
    ...overrides,
  };
}

function queued(): ApplicationResource["submissions"] {
  return [
    {
      submissionId: "01930000-0000-7000-8000-000000000004",
      performanceTitle: "Лебединое озеро",
      participantDisplayName: "Анна Иванова",
      nomination: "Хореография",
      discipline: "Классический танец",
      status: "WAITLISTED",
      priceAmount: null,
      currency: null,
    },
  ];
}

function registration(overrides: Partial<Registration> = {}): Registration {
  return { registrationOpen: true, waitlistOpen: false, ...overrides } as Registration;
}

describe("canApplicantEditApplication", () => {
  it("lets the applicant edit while registration runs", () => {
    expect(canApplicantEditApplication(application(), registration())).toBe(true);
  });

  it("keeps a paid order editable — the fee is not a seal", () => {
    expect(canApplicantEditApplication(application({ status: "PAID" }), registration())).toBe(true);
  });

  it("closes editing once registration is over", () => {
    expect(
      canApplicantEditApplication(application(), registration({ registrationOpen: false })),
    ).toBe(false);
  });

  it("keeps the fix the organizer asked for reachable after the close", () => {
    expect(
      canApplicantEditApplication(
        application({ hasCorrections: true }),
        registration({ registrationOpen: false }),
      ),
    ).toBe(true);
  });

  it("keeps a queued order editable while its queue is open", () => {
    expect(
      canApplicantEditApplication(
        application({ submissions: queued() }),
        registration({ registrationOpen: false, waitlistOpen: true }),
      ),
    ).toBe(true);
  });

  it("does not let a queue left for latecomers reopen an order already in the festival", () => {
    expect(
      canApplicantEditApplication(
        application(),
        registration({ registrationOpen: false, waitlistOpen: true }),
      ),
    ).toBe(false);
  });

  it("has nothing to edit in a finished or cancelled order", () => {
    expect(canApplicantEditApplication(application({ status: "COMPLETED" }), registration())).toBe(
      false,
    );
    expect(canApplicantEditApplication(application({ status: "CANCELLED" }), registration())).toBe(
      false,
    );
  });

  it("waits for the registration projection rather than guessing", () => {
    expect(canApplicantEditApplication(application(), undefined)).toBe(false);
  });
});
