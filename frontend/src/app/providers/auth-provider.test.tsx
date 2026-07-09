import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { emitSessionEvent, tokenStore } from "@/shared/api";
import { AuthProvider, useAuth } from "./auth-provider";

/**
 * Integration coverage for the proactive-restoration bootstrap. The current-user
 * query is the single source of truth. A URL-routing `fetch` stub distinguishes
 * the two calls the flow can make — `POST /auth/token/refresh` and
 * `GET /users/me` — so each cold-start case can assert exactly which fired.
 */

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const USER_BODY = {
  data: {
    user: {
      id: "1",
      type: "user",
      email: "u@e.com",
      displayName: "Ирина",
      status: "active",
      emailVerified: true,
    },
    staffMembership: null,
  },
};

interface Routes {
  refresh?: () => Response;
  me?: () => Response;
}

/** Extract a URL string whether `fetch` got a string, URL, or Request. */
function urlOf(input: unknown): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  if (input instanceof Request) return input.url;
  return String(input);
}

/** A `fetch` mock that answers by URL; unmatched routes 404. */
function routingFetch(routes: Routes) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = urlOf(input);
    if (url.includes("/auth/token/refresh")) {
      return routes.refresh?.() ?? new Response(null, { status: 401 });
    }
    if (url.includes("/users/me")) {
      return routes.me?.() ?? new Response(null, { status: 401 });
    }
    return new Response(null, { status: 404 });
  });
}

function Probe(): React.JSX.Element {
  const { status, user, sessionExpired } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.displayName ?? "—"}</span>
      <span data-testid="expired">{String(sessionExpired)}</span>
    </div>
  );
}

function renderProvider(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
    { wrapper },
  );
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

describe("AuthProvider bootstrap", () => {
  // Case A: cold start with a valid refresh cookie → refresh 200, then /me 200,
  // and crucially no initial 401 (GET /me is never called before the refresh).
  it("restores the session via refresh before fetching the user (no initial 401)", async () => {
    const fetchSpy = routingFetch({
      refresh: () => jsonResponse(200, { data: { accessToken: "fresh-token" } }),
      me: () => jsonResponse(200, USER_BODY),
    });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user")).toHaveTextContent("Ирина");
    expect(tokenStore.get()).toBe("fresh-token");

    const urls = fetchSpy.mock.calls.map((c) => urlOf(c[0]));
    // Refresh happened first; /me happened after; neither returned 401.
    expect(urls.some((u) => u.includes("/auth/token/refresh"))).toBe(true);
    expect(urls.some((u) => u.includes("/users/me"))).toBe(true);
    expect(urls[0]).toContain("/auth/token/refresh");
  });

  // Case B: cold start with no refresh cookie → refresh 401 → anonymous, and
  // GET /users/me is never attempted (no wasted 401 on /me).
  it("attempts refresh then settles anonymous without hitting /users/me", async () => {
    const fetchSpy = routingFetch({
      refresh: () => new Response(null, { status: 401 }),
    });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    const urls = fetchSpy.mock.calls.map((c) => urlOf(c[0]));
    expect(urls.some((u) => u.includes("/auth/token/refresh"))).toBe(true);
    expect(urls.some((u) => u.includes("/users/me"))).toBe(false);
    expect(tokenStore.get()).toBeNull();
    expect(screen.getByTestId("expired")).toHaveTextContent("false");
  });

  // Case C: a valid in-memory access token already exists → fetch /me directly,
  // no refresh call at all.
  it("fetches the user directly and skips refresh when a token is in memory", async () => {
    tokenStore.set("access-token");
    const fetchSpy = routingFetch({ me: () => jsonResponse(200, USER_BODY) });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user")).toHaveTextContent("Ирина");
    const urls = fetchSpy.mock.calls.map((c) => urlOf(c[0]));
    expect(urls.some((u) => u.includes("/auth/token/refresh"))).toBe(false);
    expect(urls.some((u) => u.includes("/users/me"))).toBe(true);
  });

  it("becomes unauthenticated + expired on a session-expired event", async () => {
    tokenStore.set("access-token");
    globalThis.fetch = routingFetch({
      me: () => jsonResponse(200, USER_BODY),
    }) as unknown as typeof fetch;

    renderProvider();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));

    emitSessionEvent("session-expired");

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(screen.getByTestId("expired")).toHaveTextContent("true");
    expect(tokenStore.get()).toBeNull();
  });
});
