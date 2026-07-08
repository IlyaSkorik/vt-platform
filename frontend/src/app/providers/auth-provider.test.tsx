import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { emitSessionEvent, tokenStore } from "@/shared/api";
import { AuthProvider, useAuth } from "./auth-provider";

/**
 * Integration coverage for the session lifecycle: the current-user query is the
 * single source of truth. We drive `GET /users/me` via a stubbed `fetch` and a
 * seeded token/remember-me flag, then assert the derived status. A
 * `session-expired` event must flip the provider to unauthenticated + expired.
 */

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
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
  tokenStore.setRememberMe(false);
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  tokenStore.clear();
  tokenStore.setRememberMe(false);
  vi.restoreAllMocks();
});

describe("AuthProvider", () => {
  it("is unauthenticated without a token or remember-me (no bootstrap request)", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("bootstraps to authenticated when a token resolves the current user", async () => {
    tokenStore.set("access-token");
    globalThis.fetch = vi.fn(async () =>
      jsonResponse(200, {
        data: {
          id: "1",
          type: "user",
          email: "u@e.com",
          displayName: "Ирина",
          status: "active",
          emailVerified: true,
        },
      }),
    ) as unknown as typeof fetch;

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user")).toHaveTextContent("Ирина");
  });

  it("becomes unauthenticated + expired on a session-expired event", async () => {
    tokenStore.set("access-token");
    globalThis.fetch = vi.fn(async () =>
      jsonResponse(200, {
        data: {
          id: "1",
          type: "user",
          email: "u@e.com",
          displayName: "Ирина",
          status: "active",
          emailVerified: true,
        },
      }),
    ) as unknown as typeof fetch;

    renderProvider();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));

    emitSessionEvent("session-expired");

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(screen.getByTestId("expired")).toHaveTextContent("true");
    expect(tokenStore.get()).toBeNull();
  });
});
