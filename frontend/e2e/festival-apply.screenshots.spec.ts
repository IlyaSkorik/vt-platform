import path from "node:path";
import { expect, type Page, test } from "@playwright/test";

/**
 * Visual capture of the applicant's Registration Wizard — the screen an applicant
 * fills a festival entry on, and the one they fill it on from a phone. Runs against
 * the preview server with every API call mocked, so it needs neither a backend nor a
 * real session:
 *   - `/auth/token/refresh` + `/users/me` fake an authenticated participant,
 *   - `/public/competitions/:id/registration` returns the projection the wizard is
 *     driven by (taxonomy, admission rules, services, consents, upload rules),
 *   - `/applications` + `/applications/:id` + `/submissions/:id` return a DRAFT with
 *     one filled performance and one untouched, so both a full and an empty card are
 *     captured.
 *
 * The fixture is deliberately unkind: long titles, a collective with a roster, a
 * long attachment filename and a priced performance. A phone is the primary device
 * here (ARCH-001 §4.5), and those are what actually break a row.
 */

const screenshotDir = path.join(process.cwd(), "docs/screenshots/festival-apply");

const FESTIVAL_ID = "01900000-0000-7000-8000-000000000001";
const APPLICATION_ID = "01900000-0000-7000-8000-0000000000a1";
const FILLED = "01900000-0000-7000-8000-0000000000b1";
const EMPTY = "01900000-0000-7000-8000-0000000000b2";

const NOMINATION = "01900000-0000-7000-8000-000000000010";
const DISCIPLINE = "01900000-0000-7000-8000-000000000020";
const GROUP = "01900000-0000-7000-8000-000000000030";
const AGE = "01900000-0000-7000-8000-000000000040";
const FORMAT = "01900000-0000-7000-8000-000000000050";
const SERVICE = "01900000-0000-7000-8000-000000000060";

const participant = {
  data: {
    user: {
      id: "user-1",
      email: "participant@example.com",
      displayName: "Ирина Ковалёва",
      status: "ACTIVE",
      type: "ADULT",
      emailVerified: true,
    },
    staffMembership: null,
  },
  meta: { requestId: "req-user" },
};

const registration = {
  data: {
    competition: {
      id: FESTIVAL_ID,
      title: "Взлёт талантов — весенний вокально-хореографический фестиваль",
      season: "2025/2026",
      status: "REGISTRATION_OPEN",
      venueName: "Дворец культуры",
      venueAddress: "пр. Независимости, 1",
    },
    registrationOpen: true,
    deadlines: {
      application: "2026-07-15T21:00:00Z",
      payment: null,
      musicUpload: null,
      documentUpload: null,
      correction: null,
    },
    nominations: [
      {
        id: NOMINATION,
        name: "Эстрадный вокал",
        description: null,
        sortOrder: 0,
        registrationOpen: true,
        registrationStopped: false,
        registrationOpensAt: "2026-06-01T00:00:00Z",
        registrationClosesAt: "2026-07-20T00:00:00Z",
      },
    ],
    disciplines: [
      { id: DISCIPLINE, nominationId: NOMINATION, name: "Ансамбль (от 3 человек)", sortOrder: 0 },
    ],
    ageCategories: [
      {
        id: AGE,
        participantGroupId: GROUP,
        name: "Смешанная возрастная категория",
        minAge: 7,
        maxAge: 25,
        sortOrder: 0,
        type: "MIXED",
        mixedCalculationMethod: "AVERAGE",
      },
    ],
    participantGroups: [{ id: GROUP, name: "Ансамбль", minCount: 3, maxCount: 12, sortOrder: 0 }],
    participationFormats: [{ id: FORMAT, name: "Очно", sortOrder: 0 }],
    admissionRules: [
      {
        nominationId: NOMINATION,
        disciplineId: DISCIPLINE,
        ageCategoryId: AGE,
        participantGroupId: GROUP,
        participationFormatId: FORMAT,
      },
    ],
    additionalServices: [
      {
        id: SERVICE,
        name: "Печать дополнительного диплома с доставкой",
        amount: "15.00",
        currency: "BYN",
        billingModel: "PER_APPLICATION",
        required: false,
        availableFormatIds: [FORMAT],
        description: "Дополнительный экземпляр диплома на бланке с доставкой почтой.",
      },
    ],
    requiredConsents: [
      { code: "personal_data", label: "Согласие на обработку персональных данных", required: true },
      { code: "regulations", label: "Согласие с положением фестиваля", required: true },
      { code: "media", label: "Согласие на фото- и видеосъёмку", required: false },
    ],
    uploadRequirements: [
      {
        participationFormatId: FORMAT,
        musicRequired: true,
        musicAllowedFormats: ["mp3", "wav", "m4a", "aac"],
        musicMaxUploadSizeMb: 25,
        mediaMode: "FILE_ONLY",
        mediaRequired: false,
        mediaAllowedFormats: ["mp4", "mov", "jpg", "jpeg", "png"],
        mediaMaxTotalSizeMb: 200,
        receiptRequired: false,
      },
    ],
  },
  meta: { requestId: "req-registration" },
};

const application = {
  id: APPLICATION_ID,
  type: "application",
  competitionId: FESTIVAL_ID,
  applicantId: "user-1",
  status: "DRAFT",
  hasCorrections: false,
  correctionComment: null,
  educationalOrganizationId: null,
  organizationName: null,
  submissions: [
    {
      submissionId: FILLED,
      performanceTitle: "«Крылатые качели» — вокально-хореографическая композиция",
      participantDisplayName: "Образцовый ансамбль «Первоцвет»",
      nomination: "Эстрадный вокал",
      discipline: "Ансамбль (от 3 человек)",
      status: "DRAFT",
      priceAmount: "126.00",
      currency: "BYN",
    },
    {
      submissionId: EMPTY,
      performanceTitle: "",
      participantDisplayName: "",
      nomination: "",
      discipline: "",
      status: "DRAFT",
      priceAmount: null,
      currency: null,
    },
  ],
  services: [
    {
      serviceId: SERVICE,
      name: "Печать дополнительного диплома с доставкой",
      unitAmount: "15.00",
      quantity: 1,
      lineAmount: "15.00",
      currency: "BYN",
    },
  ],
  consents: [{ code: "personal_data", version: "v1", acceptedAt: "2026-06-02T10:00:00Z" }],
  totalPrice: {
    totalAmount: "141.00",
    submissionsAmount: "126.00",
    servicesAmount: "15.00",
    currency: "BYN",
    calculatedAt: "2026-06-02T10:00:00Z",
  },
  paymentReceipts: [],
  paidAt: null,
  createdAt: "2026-06-01T10:00:00Z",
  updatedAt: "2026-06-02T10:00:00Z",
};

const filledSubmission = {
  id: FILLED,
  type: "submission",
  competitionId: FESTIVAL_ID,
  status: "DRAFT",
  performance: {
    title: "«Крылатые качели» — вокально-хореографическая композиция",
    durationSeconds: 215,
    nominationId: NOMINATION,
    disciplineId: DISCIPLINE,
    ageCategoryId: AGE,
    participantGroupId: GROUP,
    participationFormatId: FORMAT,
    comment: "Нужен выход из левой кулисы и микрофон на стойке для солистки.",
    ageComposition: "10 детей 8–11 лет и 2 педагога 30+",
  },
  participants: [
    {
      id: "01900000-0000-7000-8000-0000000000c1",
      registryParticipantId: "01900000-0000-7000-8000-0000000000d1",
      displayName: "Образцовый ансамбль «Первоцвет» Дворца культуры",
      firstName: null,
      lastName: null,
      middleName: null,
      birthDate: null,
      gender: null,
      memberCount: 5,
      members: [
        "Ковалёва Анастасия Дмитриевна",
        "Свиридова Мария Павловна",
        "Астапенко Владислав Игоревич",
      ],
    },
  ],
  teachers: [
    {
      id: "01900000-0000-7000-8000-0000000000e1",
      teacherDirectoryId: "01900000-0000-7000-8000-0000000000f1",
      firstName: "Мария",
      lastName: "Петрова-Селиванова",
      middleName: "Сергеевна",
      role: "Преподаватель эстрадного вокала",
    },
  ],
  attachments: [
    {
      id: "01900000-0000-7000-8000-000000000101",
      type: "MUSIC",
      fileReference: "s3://vt/music/krylatye-kacheli-minus-final-version-2026.mp3",
      caption: null,
    },
  ],
  statusHistory: [{ fromStatus: null, toStatus: "DRAFT", occurredAt: "2026-06-01T10:00:00Z" }],
  price: { amount: "126.00", currency: "BYN", calculatedAt: "2026-06-02T10:00:00Z" },
  createdAt: "2026-06-01T10:00:00Z",
  updatedAt: "2026-06-02T10:00:00Z",
};

const emptySubmission = {
  ...filledSubmission,
  id: EMPTY,
  performance: null,
  participants: [],
  teachers: [],
  attachments: [],
  price: null,
};

function json(body: unknown): { status: number; contentType: string; body: string } {
  return { status: 200, contentType: "application/json", body: JSON.stringify(body) };
}

async function mockWizard(page: Page): Promise<void> {
  // Decide the cookie banner in advance: it is fixed to the bottom of every page and
  // would otherwise cover the part of the wizard being looked at.
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "vt-cookie-consent",
      JSON.stringify({ analytics: false, decidedAt: "2026-06-01T10:00:00.000Z", version: 1 }),
    );
  });
  await page.route("**/api/v1/users/me", (route) => route.fulfill(json(participant)));
  await page.route("**/api/v1/auth/token/refresh", (route) =>
    route.fulfill(
      json({ data: { accessToken: "screenshot-token", tokenType: "Bearer" }, meta: {} }),
    ),
  );
  await page.route("**/api/v1/public/competitions/*/registration", (route) =>
    route.fulfill(json(registration)),
  );
  await page.route("**/api/v1/applications", (route) =>
    route.fulfill(json({ data: [application], meta: {} })),
  );
  await page.route(`**/api/v1/applications/${APPLICATION_ID}`, (route) =>
    route.fulfill(json({ data: application, meta: {} })),
  );
  await page.route(`**/api/v1/submissions/${FILLED}`, (route) =>
    route.fulfill(json({ data: filledSubmission, meta: {} })),
  );
  await page.route(`**/api/v1/submissions/${EMPTY}`, (route) =>
    route.fulfill(json({ data: emptySubmission, meta: {} })),
  );
  // The form re-prices itself on mount; answer with the price it already carries.
  await page.route("**/api/v1/submissions/*/price", (route) =>
    route.fulfill(json({ data: filledSubmission, meta: {} })),
  );
}

const viewports = [
  { name: "mobile-360", width: 360, height: 800 },
  { name: "mobile-390", width: 390, height: 844 },
  { name: "desktop-1440", width: 1440, height: 960 },
] as const;

test.describe("Festival apply wizard screenshots", () => {
  for (const viewport of viewports) {
    test(`captures the wizard on ${viewport.name}`, async ({ page }, testInfo) => {
      // One project writes the files. Each test sets the width it is about, so the same
      // three widths under the Pixel project would only rewrite them at that device's
      // pixel ratio — the same layout, at a size nobody asked for.
      test.skip(testInfo.project.name !== "chromium", "captured once, by the chromium project");
      await mockWizard(page);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/cabinet/competitions/${FESTIVAL_ID}/apply`);

      await expect(page.getByRole("heading", { name: /Взлёт талантов/ })).toBeVisible();
      await expect(page.getByText("Проверка и подача")).toBeVisible();

      await page.screenshot({
        path: path.join(screenshotDir, `${viewport.name}.png`),
        fullPage: true,
      });

      // What "едет вёрстка" means, measured. The page itself never scrolled sideways —
      // the layout clips the overflow — so the document width proves nothing: a control
      // pushed off the card is simply cut away and cannot be tapped. Every control has
      // to be *inside* the viewport, and that is what is asserted.
      const escaped = await page.evaluate(() => {
        const vw = document.documentElement.clientWidth;
        const out: { label: string; right: number }[] = [];
        const controls = document.querySelectorAll("button, a[href], input, select, textarea");
        for (const el of Array.from(controls)) {
          const rect = el.getBoundingClientRect();
          if (rect.width === 0 && rect.height === 0) continue;
          if (rect.right > vw + 1 || rect.left < -1) {
            out.push({
              label:
                el.getAttribute("aria-label") ??
                (el.textContent ?? "").trim().slice(0, 40) ??
                el.tagName,
              right: Math.round(rect.right),
            });
          }
        }
        return { vw, out };
      });
      expect(escaped.out, `controls outside the ${escaped.vw}px viewport`).toEqual([]);
    });
  }
});
