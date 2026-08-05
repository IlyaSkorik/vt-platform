import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { ROUTES } from "@/shared/config";
import {
  COOKIE_CONSENT_STORAGE_KEY,
  SIDEBAR_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from "@/shared/constants";
import { CookiesPolicyPage } from "./cookies-policy";
import { LEGAL_OPERATOR } from "./legal-facts";
import { PrivacyPolicyPage } from "./privacy-policy";

/**
 * The legal pages are published documents, so what is worth testing is not that
 * they render — it is the two ways they can quietly become wrong:
 *
 * 1. **Drift from the code they describe.** The cookie policy names cookies and
 *    browser-storage keys by their real identifiers. Rename a key in
 *    `shared/constants` and the policy becomes a false statement about the
 *    platform; these tests read the constants rather than repeating the strings.
 * 2. **Placeholders reaching production.** The Markdown sources carry `[указать …]`
 *    slots for facts only the operator can supply. A published policy must never
 *    show one.
 */

function renderPage(page: React.JSX.Element, url: string): void {
  render(<MemoryRouter initialEntries={[url]}>{page}</MemoryRouter>);
}

/** Contents links are `href="#id"`; every one must land on a section that exists. */
function expectTocAnchorsResolve(container: HTMLElement): void {
  const nav = container.querySelector("nav[aria-label='Содержание документа']");
  expect(nav).not.toBeNull();
  const targets = Array.from(nav?.querySelectorAll("a[href^='#']") ?? []).map((link) =>
    (link.getAttribute("href") ?? "").slice(1),
  );
  expect(targets.length).toBeGreaterThan(0);
  for (const id of targets) {
    expect(container.querySelector(`section#${id}`), `section#${id} отсутствует`).not.toBeNull();
  }
}

describe("PrivacyPolicyPage", () => {
  it("names the operator and the supervisory authority a subject can complain to", () => {
    renderPage(<PrivacyPolicyPage />, ROUTES.privacyPolicy);

    expect(screen.getAllByText(new RegExp(LEGAL_OPERATOR.name)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(new RegExp(LEGAL_OPERATOR.unp)).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: LEGAL_OPERATOR.email }).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/Национальный центр защиты персональных данных/).length,
    ).toBeGreaterThan(0);
  });

  it("resolves every contents link to a section", () => {
    const { container } = render(
      <MemoryRouter initialEntries={[ROUTES.privacyPolicy]}>
        <PrivacyPolicyPage />
      </MemoryRouter>,
    );
    expectTocAnchorsResolve(container);
  });

  it("links to the cookie policy, which it declares to be part of itself", () => {
    renderPage(<PrivacyPolicyPage />, ROUTES.privacyPolicy);
    const links = screen.getAllByRole("link", {
      name: /Политик(ой|е|и) использования файлов cookie/,
    });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0]).toHaveAttribute("href", ROUTES.cookiesPolicy);
  });

  it("omits the postal-address row while no address is configured", () => {
    // The row is conditional precisely so an unset address shows nothing rather
    // than a placeholder. When the operator supplies one this expectation flips —
    // and the test is the reminder that the address is still missing.
    renderPage(<PrivacyPolicyPage />, ROUTES.privacyPolicy);
    if (LEGAL_OPERATOR.postalAddress == null) {
      expect(screen.queryByText("Адрес для обращений")).toBeNull();
    } else {
      expect(screen.getByText("Адрес для обращений")).toBeInTheDocument();
    }
  });
});

describe("CookiesPolicyPage", () => {
  it("names every cookie the platform actually sets", () => {
    renderPage(<CookiesPolicyPage />, ROUTES.cookiesPolicy);

    for (const cookie of ["refresh_token", "csrftoken", "sessionid"]) {
      expect(screen.getAllByText(cookie).length, `cookie ${cookie} не описан`).toBeGreaterThan(0);
    }
  });

  it("names the browser-storage keys by the identifiers the code uses", () => {
    renderPage(<CookiesPolicyPage />, ROUTES.cookiesPolicy);

    expect(screen.getAllByText(THEME_STORAGE_KEY).length).toBeGreaterThan(0);
    expect(screen.getAllByText(SIDEBAR_STORAGE_KEY).length).toBeGreaterThan(0);
    // The consent record is itself browser storage the policy must disclose.
    expect(screen.getAllByText(COOKIE_CONSENT_STORAGE_KEY).length).toBeGreaterThan(0);
  });

  it("discloses both analytics services and where their data goes", () => {
    // The counters send data outside Belarus, which art. 9 of the Law only permits
    // on consent — so naming the services and the destination is not optional.
    renderPage(<CookiesPolicyPage />, ROUTES.cookiesPolicy);

    expect(screen.getAllByText(/Яндекс Метрика/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Google Analytics/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Российскую Федерацию/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/после получения согласия/).length).toBeGreaterThan(0);
  });

  it("resolves every contents link to a section", () => {
    const { container } = render(
      <MemoryRouter initialEntries={[ROUTES.cookiesPolicy]}>
        <CookiesPolicyPage />
      </MemoryRouter>,
    );
    expectTocAnchorsResolve(container);
  });
});

describe("published legal text", () => {
  it("contains no unresolved placeholder from the Markdown source", () => {
    const privacy = render(
      <MemoryRouter initialEntries={[ROUTES.privacyPolicy]}>
        <PrivacyPolicyPage />
      </MemoryRouter>,
    );
    const cookies = render(
      <MemoryRouter initialEntries={[ROUTES.cookiesPolicy]}>
        <CookiesPolicyPage />
      </MemoryRouter>,
    );

    for (const { container } of [privacy, cookies]) {
      const text = container.textContent ?? "";
      expect(text).not.toMatch(/\[указать/i);
      expect(text).not.toMatch(/TODO/);
      expect(text).not.toMatch(/___/);
    }
  });
});
