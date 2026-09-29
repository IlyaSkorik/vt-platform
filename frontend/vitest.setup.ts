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
 * - Stubs `ResizeObserver`, pointer capture and `scrollIntoView`, which jsdom does
 *   not implement but Radix-based controls (Checkbox, Select) use internally.
 * - Bridges the fetch API across the jsdom/Node seam (see `Request` below).
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

/**
 * Pointer capture and `scrollIntoView`, which jsdom does not implement.
 *
 * Radix's Select calls both while opening its list — the first from a pointer-down
 * handler, so the omission surfaces as an unhandled `target.hasPointerCapture is not
 * a function` rather than as a failing assertion, and it takes the whole suite with
 * it. Stubbed globally because every dropdown in the app is this one control.
 */
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}

/**
 * Bridge two gaps between the jsdom and Node halves of the fetch API. Both make a
 * request fail before it is ever issued, so every affected suite reads as if the
 * network were down whatever `fetch` was stubbed to return — and neither has
 * anything to do with what those suites are testing.
 *
 * **A relative URL has nothing to resolve against.** In production
 * `VITE_API_BASE_URL` is empty, meaning "same origin", so the client issues
 * `/api/v1/…` and the browser resolves it against the document. Here `Request`
 * comes from Node, which has no document and refuses a URL it cannot parse:
 * `Failed to parse URL from /api/v1/users/me`. Resolving against `document.baseURI`
 * is what the browser being stood in for would do, and it leaves an absolute input
 * untouched.
 *
 * This one is worth stating plainly, because it was hidden for a long time: a
 * developer with `VITE_API_BASE_URL` set to an absolute URL in their own
 * `frontend/.env` never saw it, while CI — which has no such file and therefore runs
 * the *shipping* configuration — failed on twenty tests. The suite now exercises the
 * production shape on both.
 *
 * **A signal from the other realm is refused.** `AbortSignal` comes from jsdom and
 * Node rejects one it did not create — `Expected signal to be an instance of
 * AbortSignal` — and ky always attaches a timeout signal. Nothing under test aborts
 * a request, so retrying without it yields the same Request for our purposes. The
 * retry is guarded by the throw rather than by sniffing the signal, so this half
 * disappears on its own once the runtimes agree.
 */
const NativeRequest = globalThis.Request;

function RequestWithoutRefusedSignal(input: RequestInfo | URL, init?: RequestInit): Request {
  // `new URL(input, base)` ignores the base when `input` is already absolute, so this
  // is unconditional rather than a guess about which form the caller used.
  const resolved = typeof input === "string" ? new URL(input, document.baseURI).href : input;
  try {
    return new NativeRequest(resolved, init);
  } catch (error) {
    if (!(error instanceof TypeError) || init?.signal === undefined) {
      throw error;
    }
    const { signal: _refused, ...rest } = init;
    return new NativeRequest(resolved, rest);
  }
}

RequestWithoutRefusedSignal.prototype = NativeRequest.prototype;
globalThis.Request = RequestWithoutRefusedSignal as unknown as typeof Request;
