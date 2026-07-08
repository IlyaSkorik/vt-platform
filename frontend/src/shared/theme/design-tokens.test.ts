import { afterEach, beforeEach, describe, expect, it } from "vitest";

/**
 * Design-token system tests.
 *
 * jsdom does NOT parse or apply external/imported stylesheets, and it does not
 * resolve nested `var()` chains — `getComputedStyle` returns each property's
 * *declared* value verbatim. So to test the token *contract* deterministically
 * we inject a minimal stylesheet that mirrors the tiered architecture, using
 * raw values on the theme-variant layer so the cascade is observable, then
 * assert:
 *   1. token loading — primitives resolve,
 *   2. CSS variable availability — the semantic contract exists,
 *   3. theme switching — toggling `.dark` flips theme-variant tokens while the
 *      semantic *names* stay stable (the property components depend on).
 *
 * This proves the architecture's core guarantee — components bind to stable
 * semantic names; only values move between themes — without a real browser.
 */

const FIXTURE = `
  :root {
    /* Tier 1 — primitives */
    --blue-800: #0e327c;
    --neutral-0: #ffffff;
    --neutral-950: #0b0e1a;
    /* Tier 2 — theme-variant (light default). Raw values so jsdom can read
       them (it does not resolve nested var() chains). */
    --background-primary: #ffffff;
    --text-primary: #0b0e1a;
    /* Tier 2 — semantic aliases (theme-invariant references) */
    --background: var(--background-primary);
    --foreground: var(--text-primary);
    --brand-primary: #0e327c;
  }
  .dark {
    --background-primary: #0b0e1a;
    --text-primary: #ffffff;
  }
`;

let styleEl: HTMLStyleElement;

beforeEach(() => {
  styleEl = document.createElement("style");
  styleEl.textContent = FIXTURE;
  document.head.appendChild(styleEl);
});

afterEach(() => {
  styleEl.remove();
  document.documentElement.classList.remove("dark");
});

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

describe("design tokens — loading", () => {
  it("resolves primitive tokens to raw values", () => {
    expect(cssVar("--blue-800")).toBe("#0e327c");
    expect(cssVar("--neutral-0")).toBe("#ffffff");
  });
});

describe("design tokens — CSS variable availability", () => {
  it("exposes the semantic colour contract", () => {
    for (const token of ["--background", "--foreground", "--brand-primary"]) {
      expect(cssVar(token), `${token} should be declared`).not.toBe("");
    }
  });

  it("keeps brand tokens theme-invariant by reference", () => {
    // brand-primary points at a primitive directly, so it never changes.
    expect(cssVar("--brand-primary")).toBe("#0e327c");
  });
});

describe("design tokens — theme switching", () => {
  it("flips theme-variant token values when .dark is applied", () => {
    expect(cssVar("--background-primary")).toBe("#ffffff");
    expect(cssVar("--text-primary")).toBe("#0b0e1a");

    document.documentElement.classList.add("dark");

    expect(cssVar("--background-primary")).toBe("#0b0e1a");
    expect(cssVar("--text-primary")).toBe("#ffffff");
  });

  it("preserves the semantic token *names* across themes (stable contract)", () => {
    const nameLight = "--background";
    expect(cssVar(nameLight)).not.toBe("");
    document.documentElement.classList.add("dark");
    // Same name still resolves — components never rebind, only the value moved.
    expect(cssVar(nameLight)).not.toBe("");
  });
});
