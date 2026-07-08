import { expect, test } from "@playwright/test";

/**
 * Smoke E2E — verifies the app boots and the routing/guard skeleton behaves.
 * Kept intentionally shallow during bootstrap; journey tests (register → submit
 * → score → results) are added alongside their features.
 */
test.describe("application shell", () => {
  test("landing page renders", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Взлёт талантов", level: 1 })).toBeVisible();
    await expect(page.getByRole("link", { name: "Войти" })).toBeVisible();
  });

  test("protected route redirects unauthenticated users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Вход", level: 1 })).toBeVisible();
  });

  test("unknown route shows the 404 page", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page.getByRole("heading", { name: "Страница не найдена" })).toBeVisible();
  });
});
