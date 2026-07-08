import type { Decorator } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { tokenStore } from "@/shared/api";

/**
 * Storybook helpers for the auth forms.
 *
 * The forms consume TanStack Query mutations and router links, so every story
 * needs a QueryClientProvider and a Router. To review the network-driven states
 * (loading, success, error) deterministically and without a backend, we stub
 * the global `fetch` — which Ky uses under the hood — per story. Retries are
 * disabled so an error renders immediately.
 */

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

/** Base decorator: fresh QueryClient + in-memory router. */
export const withAuthProviders: Decorator = (Story) => {
  tokenStore.clear();
  return (
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter>
        <div className="w-full max-w-sm">
          <Story />
        </div>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** Stub `fetch` so a submission resolves successfully (201 + minimal body). */
export function mockSuccessFetch(): void {
  globalThis.fetch = (async () =>
    jsonResponse(201, {
      data: {
        type: "session",
        accessToken: "story-access-token",
        tokenType: "Bearer",
        expiresIn: 900,
        user: { id: "1", type: "user", email: "user@example.com", displayName: "Story" },
      },
    })) as typeof fetch;
}

/** Stub `fetch` so a submission fails with an RFC 9457 Problem Details error. */
export function mockErrorFetch(status = 401): void {
  globalThis.fetch = (async () =>
    jsonResponse(status, {
      type: "https://api.vzlyot-talantov.ru/problems/authentication-failed",
      title: "Authentication failed",
      status,
      detail: "Неверный email или пароль.",
    })) as typeof fetch;
}

/** Stub `fetch` so a submission never resolves — freezes the loading state. */
export function mockPendingFetch(): void {
  globalThis.fetch = (() => new Promise<Response>(() => undefined)) as typeof fetch;
}
