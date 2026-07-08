import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { refreshAccessToken } from "./refresh";
import { tokenStore } from "./token-store";

/**
 * The shared refresh is the single source of the `POST /auth/token/refresh`
 * call. Its defining property is single-flight: concurrent callers (the 401
 * hook and the AuthProvider bootstrap) must collapse onto one network request.
 * The in-flight promise self-clears in `finally`, so awaiting each call fully
 * resets module state between tests — no `resetModules` needed (which would
 * hand back a different `tokenStore` instance than the one asserted here).
 */

const originalFetch = globalThis.fetch;

beforeEach(() => {
  tokenStore.clear();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  tokenStore.clear();
  vi.restoreAllMocks();
});

describe("refreshAccessToken", () => {
  it("stores the new access token and resolves true on success", async () => {
    globalThis.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ data: { accessToken: "fresh-token" } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    ) as unknown as typeof fetch;

    await expect(refreshAccessToken()).resolves.toBe(true);
    expect(tokenStore.get()).toBe("fresh-token");
  });

  it("resolves false and stores nothing when the cookie is rejected", async () => {
    globalThis.fetch = vi.fn(
      async () => new Response(null, { status: 401 }),
    ) as unknown as typeof fetch;

    await expect(refreshAccessToken()).resolves.toBe(false);
    expect(tokenStore.get()).toBeNull();
  });

  it("collapses concurrent callers onto a single request (single-flight)", async () => {
    const fetchSpy = vi.fn(
      async () =>
        new Response(JSON.stringify({ data: { accessToken: "fresh-token" } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    );
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    const [a, b, c] = await Promise.all([
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
    ]);

    expect([a, b, c]).toEqual([true, true, true]);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
