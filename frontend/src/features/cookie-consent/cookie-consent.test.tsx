import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import { COOKIE_CONSENT_STORAGE_KEY } from "@/shared/constants";
import { analyticsAllowed } from "./model/consent-store";
import { CookieBanner } from "./ui/cookie-banner";
import { CookieSettingsButton } from "./ui/cookie-settings-button";

/**
 * What these tests actually protect is a promise in the published cookie policy:
 * analytics counters may not load until the visitor says yes, and refusing must be
 * as available as accepting. A regression here is not a UI bug — it makes
 * `docs/legal/LEGAL-002-cookies-policy.md` §2 a false statement.
 */

function renderBanner(): void {
  render(
    <MemoryRouter>
      <CookieBanner />
    </MemoryRouter>,
  );
}

/**
 * Make the store re-read storage.
 *
 * The store keeps the decision in a module variable (a stable snapshot is what
 * `useSyncExternalStore` requires), and re-reads on a `storage` event — the same
 * mechanism that keeps other tabs in step. Tests use that lever instead of a
 * test-only escape hatch.
 */
function syncFromStorage(): void {
  window.dispatchEvent(new StorageEvent("storage", { key: COOKIE_CONSENT_STORAGE_KEY }));
}

beforeEach(() => {
  window.localStorage.clear();
  syncFromStorage();
});

describe("cookie consent", () => {
  it("withholds analytics until the visitor decides", () => {
    expect(analyticsAllowed()).toBe(false);
    renderBanner();
    expect(screen.getByRole("region", { name: /cookie/i })).toBeInTheDocument();
  });

  it("offers refusal as prominently as acceptance", () => {
    renderBanner();

    const accept = screen.getByRole("button", { name: "Принять все" });
    const refuse = screen.getByRole("button", { name: "Принять только необходимые" });

    // Equal effort and equal placement, which is what LEGAL-002 §2.3 promises: the
    // same element, the same size, side by side in one container. The colour may
    // differ; what must never appear is a refusal that costs an extra step or sits
    // somewhere else on the page.
    expect(accept.tagName).toBe(refuse.tagName);
    expect(refuse.className).toContain("h-8");
    expect(accept.className).toContain("h-8");
    expect(refuse.parentElement).toBe(accept.parentElement);
  });

  it("enables analytics only after an explicit yes, and remembers it", async () => {
    const user = userEvent.setup();
    renderBanner();

    await user.click(screen.getByRole("button", { name: "Принять все" }));

    expect(analyticsAllowed()).toBe(true);
    expect(screen.queryByRole("region", { name: /cookie/i })).toBeNull();
    expect(window.localStorage.getItem(COOKIE_CONSENT_STORAGE_KEY)).toContain('"analytics":true');
  });

  it("keeps analytics off when only necessary cookies are accepted", async () => {
    const user = userEvent.setup();
    renderBanner();

    await user.click(screen.getByRole("button", { name: "Принять только необходимые" }));

    expect(analyticsAllowed()).toBe(false);
    // The bar still goes away: a recorded "no" is a decision, not an unanswered one.
    expect(screen.queryByRole("region", { name: /cookie/i })).toBeNull();
  });

  it("lets the visitor come back and change their mind", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CookieBanner />
        <CookieSettingsButton />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "Принять все" }));
    expect(analyticsAllowed()).toBe(true);

    await user.click(screen.getByRole("button", { name: "Настройки cookie" }));

    // Withdrawal takes effect at once, and the question comes back.
    expect(analyticsAllowed()).toBe(false);
    expect(screen.getByRole("region", { name: /cookie/i })).toBeInTheDocument();
    expect(window.localStorage.getItem(COOKIE_CONSENT_STORAGE_KEY)).toBeNull();
  });

  it("re-asks when the stored decision is older than a year", () => {
    const thirteenMonthsAgo = new Date(Date.now() - 400 * 24 * 60 * 60 * 1000).toISOString();
    window.localStorage.setItem(
      COOKIE_CONSENT_STORAGE_KEY,
      JSON.stringify({ version: 1, analytics: true, decidedAt: thirteenMonthsAgo }),
    );
    syncFromStorage();

    // Consent given once and never revisited stops being informed, so an expired
    // record counts as no record — and analytics goes off with it.
    expect(analyticsAllowed()).toBe(false);
    renderBanner();
    expect(screen.getByRole("region", { name: /cookie/i })).toBeInTheDocument();
  });

  it("treats a stored decision of an older shape as no decision", () => {
    window.localStorage.setItem(
      COOKIE_CONSENT_STORAGE_KEY,
      JSON.stringify({ version: 0, analytics: true }),
    );
    syncFromStorage();

    expect(analyticsAllowed()).toBe(false);
  });

  it("honours a withdrawal made in another tab", () => {
    window.localStorage.setItem(
      COOKIE_CONSENT_STORAGE_KEY,
      JSON.stringify({ version: 1, analytics: true, decidedAt: new Date().toISOString() }),
    );
    syncFromStorage();
    expect(analyticsAllowed()).toBe(true);

    // Another tab pressed "Настройки cookie".
    window.localStorage.removeItem(COOKIE_CONSENT_STORAGE_KEY);
    syncFromStorage();

    expect(analyticsAllowed()).toBe(false);
  });
});
