import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright end-to-end configuration (ARCH-001 §28.3).
 *
 * E2E covers critical user journeys against a production-like build. Locally,
 * `webServer` boots a Vite preview of the built app; in CI these run against an
 * ephemeral stage environment via `PLAYWRIGHT_BASE_URL`.
 *
 * Mobile-first: the default projects include a mobile viewport, reflecting the
 * platform tenet that phones are the primary device (ARCH-001 §4.5).
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:4173";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 7"] },
    },
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: "pnpm preview",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
