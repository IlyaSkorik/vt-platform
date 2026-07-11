import path from "node:path";
import { expect, test } from "@playwright/test";

/**
 * Visual capture of the participant Festival Catalog at the three responsive
 * breakpoints. Runs against the dev server with every API call mocked, so it
 * needs neither a backend nor a real session:
 *   - `/auth/token/refresh` + `/users/me` fake an authenticated participant,
 *   - `/public/festivals` returns a curated fixture covering every status.
 */

const screenshotDir = path.join(process.cwd(), "docs/screenshots/festival-catalog");

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

function cover(from: string, to: string): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='640' height='400'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${from}'/><stop offset='1' stop-color='${to}'/></linearGradient></defs><rect width='640' height='400' fill='url(%23g)'/></svg>`;
  return `data:image/svg+xml,${svg.replace(/#/g, "%23").replace(/</g, "%3C").replace(/>/g, "%3E")}`;
}

function organizer(name: string) {
  return { id: "org-1", name, logo: null };
}

function festival(overrides: Record<string, unknown>) {
  return {
    id: "00000000-0000-0000-0000-000000000000",
    title: "Фестиваль",
    season: "2025/2026",
    description: null,
    status: "REGISTRATION_OPEN",
    organizer: organizer("Дом талантов"),
    city: "Минск",
    venueName: "Минск",
    venueAddress: null,
    coverImage: null,
    competitionStart: "2026-08-01",
    competitionEnd: "2026-08-03",
    registrationStart: "2026-06-01",
    registrationEnd: "2026-09-30",
    applicationDeadline: null,
    pricing: { amountFrom: "40.00", currency: "BYN", multiple: false },
    formats: [{ name: "Очно", mode: "IN_PERSON" }],
    modes: ["IN_PERSON"],
    categories: ["Вокал"],
    createdAt: "2026-05-01T10:00:00Z",
    updatedAt: "2026-05-01T10:00:00Z",
    ...overrides,
  };
}

const festivals = {
  data: [
    festival({
      id: "f-1",
      title: "Весенняя капель — вокал и хор",
      organizer: organizer("Дом талантов «Виват»"),
      city: "Минск",
      coverImage: cover("#6366f1", "#a855f7"),
      registrationEnd: "2026-07-16",
      pricing: { amountFrom: "35.00", currency: "BYN", multiple: true },
      modes: ["IN_PERSON", "ONLINE"],
      formats: [
        { name: "Очно", mode: "IN_PERSON" },
        { name: "Онлайн", mode: "ONLINE" },
      ],
      categories: ["Вокал", "Хор"],
    }),
    festival({
      id: "f-2",
      title: "Ритмы города — современный танец",
      organizer: organizer("Арт-центр «Пульс»"),
      city: "Гомель",
      coverImage: cover("#0ea5e9", "#22d3ee"),
      status: "REGISTRATION_OPEN",
      registrationEnd: "2026-10-15",
      competitionStart: "2026-11-05",
      competitionEnd: "2026-11-07",
      pricing: { amountFrom: "50.00", currency: "BYN", multiple: false },
      modes: ["IN_PERSON"],
      formats: [{ name: "Очно", mode: "IN_PERSON" }],
      categories: ["Хореография"],
    }),
    festival({
      id: "f-3",
      title: "Цифровой холст — онлайн-конкурс ИЗО",
      organizer: organizer("Студия «Радуга»"),
      city: "Брест",
      status: "COMING_SOON",
      coverImage: cover("#f59e0b", "#ef4444"),
      competitionStart: "2026-12-01",
      competitionEnd: "2026-12-10",
      registrationStart: "2026-10-01",
      registrationEnd: "2026-11-20",
      pricing: { amountFrom: "20.00", currency: "BYN", multiple: true },
      modes: ["ONLINE"],
      formats: [{ name: "Онлайн", mode: "ONLINE" }],
      categories: ["Изобразительное искусство"],
    }),
    festival({
      id: "f-4",
      title: "Инструментальная весна",
      organizer: organizer("Филармония «Соло»"),
      city: "Витебск",
      status: "REGISTRATION_CLOSED",
      coverImage: null,
      registrationEnd: "2026-06-30",
      competitionStart: "2026-07-20",
      competitionEnd: "2026-07-22",
      pricing: { amountFrom: "60.00", currency: "BYN", multiple: false },
      modes: ["HYBRID"],
      formats: [{ name: "Гибрид", mode: "HYBRID" }],
      categories: ["Инструментальное исполнительство"],
    }),
    festival({
      id: "f-5",
      title: "Театральные подмостки — 2026",
      organizer: organizer("Театр-студия «Маска»"),
      city: "Могилёв",
      status: "RUNNING",
      coverImage: cover("#10b981", "#14b8a6"),
      competitionStart: "2026-07-10",
      competitionEnd: "2026-07-14",
      pricing: { amountFrom: null, currency: null, multiple: false },
      modes: ["IN_PERSON"],
      formats: [{ name: "Очно", mode: "IN_PERSON" }],
      categories: ["Театр"],
    }),
    festival({
      id: "f-6",
      title: "Зимняя рапсодия — итоги",
      organizer: organizer("Дом талантов «Виват»"),
      city: "Минск",
      status: "COMPLETED",
      coverImage: cover("#64748b", "#94a3b8"),
      competitionStart: "2026-02-01",
      competitionEnd: "2026-02-03",
      pricing: { amountFrom: "45.00", currency: "BYN", multiple: true },
      modes: ["IN_PERSON", "ONLINE"],
      formats: [
        { name: "Очно", mode: "IN_PERSON" },
        { name: "Онлайн", mode: "ONLINE" },
      ],
      categories: ["Вокал"],
    }),
  ],
  meta: { requestId: "req-festivals" },
};

async function mockCatalog(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(participant),
    }),
  );
  await page.route("**/api/v1/auth/token/refresh", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: { accessToken: "screenshot-token", tokenType: "Bearer" },
        meta: { requestId: "req-refresh" },
      }),
    }),
  );
  await page.route("**/api/v1/public/festivals", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(festivals),
    }),
  );
}

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "tablet", width: 834, height: 1112 },
  { name: "mobile", width: 390, height: 844 },
] as const;

test.describe("Festival catalog screenshots", () => {
  for (const viewport of viewports) {
    test(`captures the catalog on ${viewport.name}`, async ({ page }) => {
      await mockCatalog(page);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/cabinet/competitions");

      await expect(page.getByRole("heading", { name: "Фестивали", level: 1 })).toBeVisible();
      await expect(page.getByText("Весенняя капель — вокал и хор").first()).toBeVisible();

      await page.screenshot({
        path: path.join(screenshotDir, `${viewport.name}.png`),
        fullPage: true,
      });
    });
  }

  test("captures the filters panel open on desktop", async ({ page }) => {
    await mockCatalog(page);
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto("/cabinet/competitions");
    await expect(page.getByText("Весенняя капель — вокал и хор").first()).toBeVisible();

    await page.getByRole("button", { name: /Фильтры/ }).click();
    await expect(page.getByText("Формат участия")).toBeVisible();

    await page.screenshot({
      path: path.join(screenshotDir, "desktop-filters.png"),
      fullPage: true,
    });
  });
});
