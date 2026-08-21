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

if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}

/**
 * Let a `Request` be built with a jsdom abort signal.
 *
 * The two halves of the fetch API come from different implementations here:
 * `Request` from Node (jsdom does not implement it) and `AbortSignal` from jsdom.
 * Node refuses a signal it did not create — `new Request(url, { signal })` throws
 * `Expected signal to be an instance of AbortSignal` — and since ky always attaches
 * a timeout signal, every suite that talks through the API client failed as if the
 * network were down, whatever `fetch` was stubbed to return.
 *
 * Nothing under test aborts a request, so retrying without the signal yields the
 * same Request for our purposes. The retry is guarded by the throw rather than by
 * sniffing the signal, so the shim disappears on its own once the runtimes agree.
 */
const NativeRequest = globalThis.Request;

function RequestWithoutRefusedSignal(input: RequestInfo | URL, init?: RequestInit): Request {
  try {
    return new NativeRequest(input, init);
  } catch (error) {
    if (!(error instanceof TypeError) || init?.signal === undefined) {
      throw error;
    }
    const { signal: _refused, ...rest } = init;
    return new NativeRequest(input, rest);
  }
}

RequestWithoutRefusedSignal.prototype = NativeRequest.prototype;
globalThis.Request = RequestWithoutRefusedSignal as unknown as typeof Request;
