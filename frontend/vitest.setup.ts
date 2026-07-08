import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

/**
 * Global test setup shared by every Vitest suite.
 *
 * - Registers `@testing-library/jest-dom` matchers (`toBeInTheDocument`, …).
 * - Unmounts the React tree after each test to keep suites isolated.
 * - Stubs `matchMedia`, which jsdom does not implement but the theme provider
 *   relies on for system colour-scheme detection.
 * - Stubs `ResizeObserver`, which jsdom does not implement but Radix-based
 *   controls (Checkbox, Select) use internally.
 */
afterEach(() => {
  cleanup();
});

if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}
