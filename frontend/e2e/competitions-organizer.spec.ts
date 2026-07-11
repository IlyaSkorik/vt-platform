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
    enabledFormats: [],
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
  });
});
