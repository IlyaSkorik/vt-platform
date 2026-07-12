import path from "node:path";
import { expect, test } from "@playwright/test";

/**
 * Visual capture of the public Competition Landing Page at the three responsive
 * breakpoints. Runs against the dev/preview server with every API call mocked,
 * so it needs neither a backend nor a real session:
 *   - `/auth/token/refresh` + `/users/me` fake an authenticated participant,
 *   - `/public/festivals/:id` returns a rich landing fixture (hero, blocks,
 *     contacts) covering every supported block type.
 */

const screenshotDir = path.join(process.cwd(), "docs/screenshots/festival-landing");

const FESTIVAL_ID = "01900000-0000-7000-8000-000000000001";

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

function image(from: string, to: string, w = 1280, h = 720): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${from}'/><stop offset='1' stop-color='${to}'/></linearGradient></defs><rect width='${w}' height='${h}' fill='url(%23g)'/></svg>`;
  return `data:image/svg+xml,${svg.replace(/#/g, "%23").replace(/</g, "%3C").replace(/>/g, "%3E")}`;
}

const detail = {
  data: {
    id: FESTIVAL_ID,
    title: "Взлёт талантов — весенний вокальный фестиваль",
    season: "2025/2026",
    description: "Международный фестиваль детского и юношеского творчества.",
    status: "REGISTRATION_OPEN",
    organizer: { id: "org-1", name: "Дом талантов «Виват»", logo: null },
    city: "Минск",
    venueName: "Дворец культуры",
    venueAddress: "пр. Независимости, 1",
    coverImage: image("#6366f1", "#a855f7"),
    competitionStart: "2026-08-01",
    competitionEnd: "2026-08-03",
    registrationStart: "2026-06-01",
    registrationEnd: "2026-07-20",
    applicationDeadline: "2026-07-15T21:00:00Z",
    pricing: { amountFrom: "35.00", currency: "BYN", multiple: true },
    formats: [
      { name: "Очно", mode: "IN_PERSON" },
      { name: "Онлайн", mode: "ONLINE" },
    ],
    modes: ["IN_PERSON", "ONLINE"],
    categories: ["Вокал", "Хор"],
    createdAt: "2026-05-01T10:00:00Z",
    updatedAt: "2026-05-01T10:00:00Z",
    regulation: {
      title: "Положение о фестивале «Взлёт талантов» 2026",
      version: "v2",
      publicationDate: "2026-05-15",
      fileReference: "/media/regulations/vzlyot-2026.pdf",
    },
    landing: {
      blocks: [
        {
          id: "hero",
          type: "HERO",
          sortOrder: 0,
          title: "Взлёт талантов",
          subtitle: "Три дня музыки, сцены и открытий для юных исполнителей со всей страны.",
          coverImage: image("#4f46e5", "#db2777"),
          body: null,
          contentFormat: null,
          jury: [],
          partners: [],
          images: [],
          faq: [],
        },
        {
          id: "about",
          type: "CONTENT",
          sortOrder: 1,
          title: "О фестивале",
          subtitle: null,
          coverImage: null,
          body: "«Взлёт талантов» — ежегодный праздник детского творчества. Участников ждут выступления на большой сцене, мастер-классы от ведущих педагогов и обратная связь от профессионального жюри.\n\nК участию приглашаются солисты и коллективы в номинациях «Вокал» и «Хоровое пение».",
          contentFormat: "PLAIN",
          jury: [],
          partners: [],
          images: [],
          faq: [],
        },
        {
          id: "jury",
          type: "JURY",
          sortOrder: 2,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          jury: [
            {
              id: "j1",
              name: "Анна Соколова",
              photo: image("#f59e0b", "#ef4444", 200, 200),
              position: "Народная артистка, председатель жюри",
              description: "Более 20 лет в вокальной педагогике.",
            },
            {
              id: "j2",
              name: "Дмитрий Орлов",
              photo: image("#0ea5e9", "#22d3ee", 200, 200),
              position: "Дирижёр, хормейстер",
              description: null,
            },
            {
              id: "j3",
              name: "Мария Кузнецова",
              photo: null,
              position: "Лауреат международных конкурсов",
              description: "Специалист по эстрадному вокалу.",
            },
          ],
          partners: [],
          images: [],
          faq: [],
        },
        {
          id: "partners",
          type: "PARTNERS",
          sortOrder: 3,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          jury: [],
          partners: [
            { id: "p1", name: "Министерство культуры", logo: null, website: "https://example.org" },
            { id: "p2", name: "Филармония", logo: null, website: null },
            {
              id: "p3",
              name: "Музыкальный магазин «Нота»",
              logo: null,
              website: "https://example.org",
            },
          ],
          images: [],
          faq: [],
        },
        {
          id: "gallery",
          type: "GALLERY",
          sortOrder: 4,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          jury: [],
          partners: [],
          images: [
            { id: "g1", url: image("#6366f1", "#a855f7", 400, 400), caption: "Гала-концерт 2025" },
            { id: "g2", url: image("#0ea5e9", "#22d3ee", 400, 400), caption: "Мастер-класс" },
            { id: "g3", url: image("#10b981", "#14b8a6", 400, 400), caption: "Награждение" },
            { id: "g4", url: image("#f59e0b", "#ef4444", 400, 400), caption: "На сцене" },
            { id: "g5", url: image("#8b5cf6", "#ec4899", 400, 400), caption: "Репетиция" },
            { id: "g6", url: image("#14b8a6", "#0ea5e9", 400, 400), caption: "Финал" },
            { id: "g7", url: image("#f43f5e", "#f59e0b", 400, 400), caption: null },
          ],
          faq: [],
        },
        {
          id: "faq",
          type: "FAQ",
          sortOrder: 5,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          jury: [],
          partners: [],
          images: [],
          faq: [
            {
              id: "q1",
              question: "Кто может принять участие?",
              answer: "Солисты и коллективы в возрасте от 6 до 18 лет.",
            },
            {
              id: "q2",
              question: "Как подать заявку?",
              answer: "Нажмите «Подать заявку» и заполните форму регистрации.",
            },
          ],
        },
        {
          id: "venue",
          type: "VENUE",
          sortOrder: 6,
          title: null,
          subtitle: null,
          coverImage: null,
          body: null,
          contentFormat: null,
          jury: [],
          partners: [],
          images: [],
          faq: [],
        },
      ],
    },
    contacts: {
      organizationName: "Дом талантов «Виват»",
      phone: "+375 29 123-45-67",
      email: "hello@vivat.by",
      website: "https://vivat.by",
      address: "г. Минск, пр. Независимости, 1",
      social: {
        vk: "https://vk.com/vivat",
        telegram: "https://t.me/vivat",
        instagram: null,
      },
      team: [
        {
          id: "t1",
          name: "Ольга Смирнова",
          position: "Координатор фестиваля",
          phone: "+375 29 765-43-21",
          email: "olga@vivat.by",
          description: null,
        },
      ],
      emergency: { phone: null, email: null, notes: null },
      venue: {
        name: "Дворец культуры",
        address: "пр. Независимости, 1",
        city: "Минск",
        country: "Беларусь",
        googleMapsUrl: "https://maps.google.com/?q=fest",
        yandexMapsUrl: "https://yandex.by/maps/?text=fest",
        directions: "5 минут пешком от станции метро «Площадь Победы».",
      },
    },
  },
  meta: { requestId: "req-detail" },
};

async function mockLanding(page: import("@playwright/test").Page) {
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
  await page.route("**/api/v1/public/festivals/*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detail),
    }),
  );
}

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "tablet", width: 834, height: 1112 },
  { name: "mobile", width: 390, height: 844 },
] as const;

test.describe("Festival landing screenshots", () => {
  for (const viewport of viewports) {
    test(`captures the landing on ${viewport.name}`, async ({ page }) => {
      await mockLanding(page);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/cabinet/competitions/${FESTIVAL_ID}`);

      await expect(page.getByRole("heading", { name: "Взлёт талантов", level: 1 })).toBeVisible();
      await expect(page.getByRole("heading", { name: "О фестивале", exact: true })).toBeVisible();

      await page.screenshot({
        path: path.join(screenshotDir, `${viewport.name}.png`),
        fullPage: true,
      });
    });
  }

  test("opens a gallery photo in the lightbox", async ({ page }) => {
    await mockLanding(page);
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto(`/cabinet/competitions/${FESTIVAL_ID}`);

    await page.getByRole("button", { name: /Открыть фото: Гала-концерт 2025/ }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Следующее фото" })).toBeVisible();

    await page.screenshot({ path: path.join(screenshotDir, "lightbox.png") });
  });
});
