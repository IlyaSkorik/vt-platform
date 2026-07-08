import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { onSessionEvent, tokenStore } from "@/shared/api";
import { refreshOnUnauthorized } from "./refresh-on-unauthorized";

/**
 * The hook receives Ky's `AfterResponseState`; we only exercise `request` and
 * `response`. A `401` on a protected path triggers a single refresh, then
 * replays the original request with the new token. Auth paths and already-
 * retried requests are passed through untouched.
 */
type HookState = Parameters<typeof refreshOnUnauthorized>[0];

function state(url: string, status: number, headers: Record<string, string> = {}): HookState {
  return {
    request: new Request(url, { headers }),
    response: new Response(null, { status }),
    options: {} as HookState["options"],
    retryCount: 0,
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const originalFetch = globalThis.fetch;

beforeEach(() => {
  tokenStore.clear();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  tokenStore.clear();
  vi.restoreAllMocks();
});

describe("refreshOnUnauthorized", () => {
  it("passes through non-401 responses untouched", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const input = state("https://api.test/api/v1/users/me", 200);
    const result = await refreshOnUnauthorized(input);
    expect(result).toBe(input.response);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not refresh a 401 from an auth endpoint (bad credentials)", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const input = state("https://api.test/api/v1/auth/sessions", 401);
    const result = await refreshOnUnauthorized(input);
    expect(result).toBe(input.response);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("refreshes on a protected 401, stores the new token, and replays the request", async () => {
    const fetchSpy = vi
      .fn()
      // 1) the refresh call
      .mockResolvedValueOnce(jsonResponse(200, { data: { accessToken: "fresh-token" } }))
      // 2) the replayed original request
      .mockResolvedValueOnce(jsonResponse(200, { data: { id: "1" } }));
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    const input = state("https://api.test/api/v1/users/me", 401);
    const result = await refreshOnUnauthorized(input);

    expect(tokenStore.get()).toBe("fresh-token");
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect((result as Response).status).toBe(200);
  });

  it("emits session-expired and clears the token when the refresh fails", async () => {
    globalThis.fetch = vi.fn(
      async () => new Response(null, { status: 401 }),
    ) as unknown as typeof fetch;
    tokenStore.set("stale");
    const listener = vi.fn();
    const unsubscribe = onSessionEvent("session-expired", listener);

    const input = state("https://api.test/api/v1/users/me", 401);
    await refreshOnUnauthorized(input);

    expect(listener).toHaveBeenCalledTimes(1);
    expect(tokenStore.get()).toBeNull();
    unsubscribe();
  });

  it("does not attempt a second refresh on an already-retried request", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const input = state("https://api.test/api/v1/users/me", 401, { "X-VT-Refresh-Retry": "1" });
    const result = await refreshOnUnauthorized(input);
    expect(result).toBe(input.response);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
