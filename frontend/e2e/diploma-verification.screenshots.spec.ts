import path from "node:path";
import { expect, type Page, test } from "@playwright/test";

/**
 * Visual capture of the public diploma verification page at the three responsive
 * breakpoints, in both themes and in every result state.
 *
 * Runs against the dev/preview server with the register call mocked, so it needs
 * neither a backend nor a session — the page is unauthenticated by design, so
 * unlike the landing captures there is nothing to fake but the one endpoint.
 */

const screenshotDir = path.join(process.cwd(), "docs/screenshots/diploma-verification");

const TOKEN = "Q0hFQ0stVEhJUy1ESVBMT01BLVRPS0VO";

/** A register entry with the long values the layout has to survive. */
const verified = {
  data: {
    number: "VT-2026-000001",
    participantName: "Иванов Иван Иванович",
    competitionTitle: "Международный конкурс «Взлёт талантов»",
    competitionDate: "12.04.2026",
    nomination: "Вокал",
    performance: "Катюша",
    teacher: "Петрова Ольга Сергеевна",
    organization: "ДШИ №1 г. Минска",
    degree: "Лауреат I степени",
    issueDate: "2026-04-20T12:00:00Z",
    officialPdfUrl: "/media/diplomas/official/VT-2026-000001.pdf",
    verified: true,
  },
  meta: { requestId: "req-verify" },
};

const notFound = {
  type: "https://api.vzlyot-talantov.ru/problems/not-found",
  title: "Resource not found",
  status: 404,
  detail: "No diploma matches this verification token.",
  instance: `/api/v1/public/diplomas/verify/${TOKEN}`,
  requestId: "req-verify-404",
};

async function mockRegister(page: Page, body: unknown, status = 200): Promise<void> {
  await page.route("**/api/v1/public/diplomas/verify/*", (route) =>
    route.fulfill({
      status,
      contentType: status === 200 ? "application/json" : "application/problem+json",
      body: JSON.stringify(body),
    }),
  );
}

/** Pin the theme so a capture never depends on the runner's OS preference. */
async function useTheme(page: Page, theme: "light" | "dark"): Promise<void> {
  await page.addInitScript((value) => {
    window.localStorage.setItem("vt-theme", value);
  }, theme);
  await page.emulateMedia({ colorScheme: theme });
}

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "tablet", width: 834, height: 1112 },
  { name: "mobile", width: 390, height: 844 },
] as const;

test.describe("Diploma verification screenshots", () => {
  for (const viewport of viewports) {
    test(`captures a confirmed diploma on ${viewport.name}`, async ({ page }) => {
      await useTheme(page, "light");
      await mockRegister(page, verified);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/verify/${TOKEN}`);

      await expect(page.getByRole("heading", { name: "Диплом подтверждён" })).toBeVisible();
      await expect(page.getByText("VT-2026-000001")).toBeVisible();

      await page.screenshot({
        path: path.join(screenshotDir, `${viewport.name}.png`),
        fullPage: true,
      });
    });
  }

  test("captures a confirmed diploma in the dark theme", async ({ page }) => {
    await useTheme(page, "dark");
    await mockRegister(page, verified);
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto(`/verify/${TOKEN}`);

    await expect(page.getByRole("heading", { name: "Диплом подтверждён" })).toBeVisible();
    await page.screenshot({ path: path.join(screenshotDir, "desktop-dark.png"), fullPage: true });
  });

  test("captures a diploma whose results are not published yet", async ({ page }) => {
    await useTheme(page, "light");
    await mockRegister(page, {
      ...verified,
      data: { ...verified.data, degree: null, officialPdfUrl: null },
    });
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto(`/verify/${TOKEN}`);

    await expect(page.getByText("Результаты конкурса ещё не опубликованы")).toBeVisible();
    // No official PDF yet, so no download offered.
    await expect(page.getByRole("link", { name: /Скачать/ })).toHaveCount(0);

    await page.screenshot({ path: path.join(screenshotDir, "pending-degree.png"), fullPage: true });
  });

  test("captures the not-found record", async ({ page }) => {
    await useTheme(page, "light");
    await mockRegister(page, notFound, 404);
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto(`/verify/${TOKEN}`);

    await expect(page.getByRole("heading", { name: "Диплом не найден" })).toBeVisible();
    await page.screenshot({ path: path.join(screenshotDir, "not-found.png"), fullPage: true });
  });

  test("captures the not-found record on mobile", async ({ page }) => {
    await useTheme(page, "light");
    await mockRegister(page, notFound, 404);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/verify/${TOKEN}`);

    await expect(page.getByRole("heading", { name: "Диплом не найден" })).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDir, "not-found-mobile.png"),
      fullPage: true,
    });
  });
});
