import path from "node:path";
import { expect, test } from "@playwright/test";

const screenshotDir = path.join(process.cwd(), "docs/screenshots/organizer-workspace");

const staffUser = {
  data: {
    user: {
      id: "user-1",
      email: "organizer@example.com",
      firstName: "Organizer",
      lastName: "User",
      status: "ACTIVE",
      type: "ADULT",
      emailVerified: true,
    },
    staffMembership: {
      role: "COMPETITION_MANAGER",
      status: "ACTIVE",
    },
  },
  meta: { requestId: "req-user" },
};

const competitionDetail = {
  data: {
    id: "comp-1",
    title: "Spring Talent Festival",
    season: "2025/2026",
    status: "DRAFT",
    organizerId: "org-1",
    description: "A showcase for young performers.",
    branding: { logo: null, banner: null, poster: null },
    venue: { name: "Grand Hall", address: "Moscow, Example st. 1" },
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
    participationFormats: [
      {
        id: "fmt-1",
        name: "Очно",
        description: "Выступление на площадке фестиваля",
        enabled: true,
        sortOrder: 0,
      },
      {
        id: "fmt-2",
        name: "Онлайн",
        description: "Удалённое участие",
        enabled: true,
        sortOrder: 1,
      },
      {
        id: "fmt-3",
        name: "Video Submission",
        description: "Запись заранее",
        enabled: false,
        sortOrder: 2,
      },
    ],
    categories: [
      {
        id: "cat-1",
        name: "Вокал",
        description: "Сольные и ансамблевые вокальные направления",
        sortOrder: 0,
      },
      {
        id: "cat-2",
        name: "Хореография",
        description: null,
        sortOrder: 1,
      },
    ],
    disciplines: [
      { id: "dis-1", categoryId: "cat-1", name: "Эстрадный вокал", sortOrder: 0 },
      { id: "dis-2", categoryId: "cat-1", name: "Академический вокал", sortOrder: 1 },
      { id: "dis-3", categoryId: "cat-1", name: "Народный вокал", sortOrder: 2 },
      { id: "dis-4", categoryId: "cat-2", name: "Классика", sortOrder: 0 },
      { id: "dis-5", categoryId: "cat-2", name: "Contemporary", sortOrder: 1 },
      { id: "dis-6", categoryId: "cat-2", name: "Народный танец", sortOrder: 2 },
    ],
    ageCategories: [
      {
        id: "a1",
        categoryId: "cat-1",
        name: "4–6 лет",
        minAge: 4,
        maxAge: 6,
        sortOrder: 0,
        type: "STANDARD",
        mixedCalculationMethod: null,
      },
      {
        id: "a2",
        categoryId: "cat-1",
        name: "7–9 лет",
        minAge: 7,
        maxAge: 9,
        sortOrder: 1,
        type: "STANDARD",
        mixedCalculationMethod: null,
      },
      {
        id: "a3",
        categoryId: "cat-2",
        name: "10–12 лет",
        minAge: 10,
        maxAge: 12,
        sortOrder: 2,
        type: "STANDARD",
        mixedCalculationMethod: null,
      },
    ],
    participantGroups: [
      {
        id: "pg-1",
        categoryId: "cat-1",
        name: "Solo",
        minCount: 1,
        maxCount: 1,
        description: "Один участник",
        sortOrder: 0,
      },
      {
        id: "pg-2",
        categoryId: "cat-1",
        name: "Duet",
        minCount: 2,
        maxCount: 2,
        description: null,
        sortOrder: 1,
      },
      {
        id: "pg-3",
        categoryId: "cat-1",
        name: "Ensemble",
        minCount: 5,
        maxCount: 12,
        description: "Малый состав",
        sortOrder: 2,
      },
      {
        id: "pg-4",
        categoryId: "cat-2",
        name: "Solo",
        minCount: 1,
        maxCount: 1,
        description: null,
        sortOrder: 0,
      },
      {
        id: "pg-5",
        categoryId: "cat-2",
        name: "Choir",
        minCount: 13,
        maxCount: 40,
        description: "Хоровой состав",
        sortOrder: 1,
      },
    ],
    admissionRules: [
      {
        categoryId: "cat-1",
        disciplineId: "dis-1",
        ageCategoryId: "a1",
        participantGroupId: "pg-1",
        participationFormatId: "fmt-1",
      },
      {
        categoryId: "cat-1",
        disciplineId: "dis-1",
        ageCategoryId: "a2",
        participantGroupId: "pg-1",
        participationFormatId: "fmt-1",
      },
      {
        categoryId: "cat-1",
        disciplineId: "dis-1",
        ageCategoryId: "a2",
        participantGroupId: "pg-2",
        participationFormatId: "fmt-2",
      },
    ],
    pricingRules: [
      {
        categoryId: "cat-1",
        disciplineId: "dis-1",
        ageCategoryId: "a1",
        participantGroupId: "pg-1",
        participationFormatId: "fmt-1",
        amount: "50.00",
        currency: "BYN",
        calculationType: "PER_PARTICIPANT",
      },
      {
        categoryId: "cat-1",
        disciplineId: "dis-1",
        ageCategoryId: "a2",
        participantGroupId: "pg-1",
        participationFormatId: "fmt-1",
        amount: "45.00",
        currency: "BYN",
        calculationType: "PER_PERFORMANCE",
      },
    ],
    regulations: [],
    currentRegulationId: null,
    documents: [],
    additionalServices: [],
    contacts: [
      { id: "c1", type: "WEBSITE", value: "https://example.com", isPrimary: true },
      { id: "c2", type: "VK", value: "https://vk.com/example", isPrimary: false },
    ],
    informationBlocks: [],
    createdAt: "2026-01-01T10:00:00.000Z",
    updatedAt: "2026-01-10T12:00:00.000Z",
    version: 3,
  },
  meta: { requestId: "req-detail" },
};

const competitionList = {
  data: [
    {
      id: "comp-1",
      title: "Spring Talent Festival",
      season: "2025/2026",
      status: "DRAFT",
      organizerId: "org-1",
      description: "A showcase for young performers.",
      createdAt: "2026-01-01T10:00:00.000Z",
      updatedAt: "2026-01-10T12:00:00.000Z",
      version: 3,
    },
    {
      id: "comp-2",
      title: "Winter Dance Cup",
      season: "2024/2025",
      status: "REGISTRATION_OPEN",
      organizerId: "org-1",
      description: null,
      createdAt: "2025-11-01T10:00:00.000Z",
      updatedAt: "2026-01-08T09:00:00.000Z",
      version: 5,
    },
  ],
  meta: { requestId: "req-list" },
};

async function mockStaffApi(
  page: import("@playwright/test").Page,
  options?: { emptyList?: boolean },
) {
  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(staffUser),
    });
  });
  await page.route("**/api/v1/auth/token/refresh", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: { accessToken: "mock-token", tokenType: "Bearer" },
        meta: { requestId: "req-refresh" },
      }),
    });
  });
  await page.route("**/api/v1/competitions", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        options?.emptyList ? { data: [], meta: { requestId: "req-empty" } } : competitionList,
      ),
    });
  });
  await page.route("**/api/v1/competitions/comp-1", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(competitionDetail),
    });
  });
}

test.describe("Organizer workspace screenshots", () => {
  test("capture competitions management screens", async ({ page }) => {
    await mockStaffApi(page);

    await page.goto("/staff/competitions");
    await expect(page.getByRole("heading", { name: "Фестивали", level: 1 })).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "01-competitions-page.png"),
      fullPage: true,
    });

    await mockStaffApi(page, { emptyList: true });
    await page.route("**/api/v1/competitions", async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [], meta: { requestId: "req-empty" } }),
      });
    });
    await page.reload();
    await expect(page.getByText("Пока нет фестивалей")).toBeVisible();
    await page.screenshot({ path: path.join(screenshotDir, "02-empty-state.png"), fullPage: true });

    await mockStaffApi(page);
    await page.goto("/staff/competitions/comp-1?section=general");
    await expect(
      page.getByRole("heading", { name: "Spring Talent Festival", level: 1 }),
    ).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "03-competition-workspace.png"),
      fullPage: true,
    });

    await expect(page.getByLabel("Название фестиваля")).toHaveValue("Spring Talent Festival");
    await page.screenshot({
      path: path.join(screenshotDir, "04-general-section.png"),
      fullPage: true,
    });

    await page.goto("/staff/competitions/comp-1?section=categories");
    await expect(page.getByRole("heading", { name: "Номинации и дисциплины" })).toBeVisible();
    await expect(page.getByText("Вокал")).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "05-categories-desktop.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 820, height: 1180 });
    await page.screenshot({
      path: path.join(screenshotDir, "05-categories-tablet.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(screenshotDir, "05-categories-mobile.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/staff/competitions/comp-1?section=age-categories");
    await expect(page.getByRole("heading", { name: "Возрастные категории" })).toBeVisible();
    await expect(page.getByText("4–6 лет")).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "06-age-categories-desktop.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 820, height: 1180 });
    await page.screenshot({
      path: path.join(screenshotDir, "06-age-categories-tablet.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(screenshotDir, "06-age-categories-mobile.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/staff/competitions/comp-1?section=participant-groups");
    await expect(page.getByRole("heading", { name: "Группы участников" })).toBeVisible();
    await expect(page.getByText("Ensemble")).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "07-participant-groups-desktop.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 820, height: 1180 });
    await page.screenshot({
      path: path.join(screenshotDir, "07-participant-groups-tablet.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(screenshotDir, "07-participant-groups-mobile.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/staff/competitions/comp-1?section=participation-formats");
    await expect(page.getByRole("heading", { name: "Форматы участия" })).toBeVisible();
    await expect(page.getByText("Video Submission")).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "08-participation-formats-desktop.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 820, height: 1180 });
    await page.screenshot({
      path: path.join(screenshotDir, "08-participation-formats-tablet.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(screenshotDir, "08-participation-formats-mobile.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/staff/competitions/comp-1?section=admission-rules");
    await expect(page.getByRole("heading", { name: "Правила допуска" })).toBeVisible();
    await expect(page.getByText("Эстрадный вокал")).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "09-admission-rules-desktop.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 820, height: 1180 });
    await page.screenshot({
      path: path.join(screenshotDir, "09-admission-rules-tablet.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(screenshotDir, "09-admission-rules-mobile.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/staff/competitions/comp-1?section=pricing");
    await expect(page.getByRole("heading", { name: "Цены" })).toBeVisible();
    await expect(page.getByText("Цена за участника").first()).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "10-pricing-desktop.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 820, height: 1180 });
    await page.screenshot({
      path: path.join(screenshotDir, "10-pricing-tablet.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(screenshotDir, "10-pricing-mobile.png"),
      fullPage: true,
    });
  });
});
