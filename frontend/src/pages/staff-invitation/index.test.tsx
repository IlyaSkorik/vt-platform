import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { tokenStore } from "@/shared/api";
import { StaffInvitationPage } from "./index";

const authState = {
  status: "authenticated" as "loading" | "authenticated" | "unauthenticated",
  staffMembership: null as null | { role: string; status: string },
  refresh: vi.fn(async () => undefined),
  signOut: vi.fn(async () => undefined),
};

vi.mock("@/app/providers", () => ({
  useAuth: () => ({
    status: authState.status,
    user:
      authState.status === "authenticated"
        ? { id: "u1", email: "staff@example.com", displayName: "Staff" }
        : null,
    staffMembership: authState.staffMembership,
    isStaff: authState.staffMembership?.status === "ACTIVE",
    isAuthenticated: authState.status === "authenticated",
    sessionExpired: false,
    refresh: authState.refresh,
    signOut: authState.signOut,
  }),
}));

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "x-request-id": `req-${status}` },
  });
}

function problem(status: number): Response {
  return jsonResponse(status, {
    type: "https://api.vzlyot-talantov.ru/problems/test",
    title: "Problem",
    status,
    detail: "Problem",
    requestId: `req-${status}`,
  });
}

const invitation = {
  organizationName: "Взлёт талантов",
  role: "DIRECTOR",
  invitedEmail: "staff@example.com",
  expiresAt: "2026-07-20T12:00:00Z",
};

function urlOf(input: unknown): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  if (input instanceof Request) return input.url;
  return String(input);
}

function renderPage(url = "/staff/invitations/token-123"): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[url]}>
          <Routes>
            <Route path="/staff/invitations/:token" element={<StaffInvitationPage />} />
            <Route path="/login" element={<p>LOGIN</p>} />
            <Route path="/cabinet" element={<p>Панель кабинета</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    ) as ReactNode,
  );
  return queryClient;
}

const originalFetch = globalThis.fetch;

beforeEach(() => {
  authState.status = "authenticated";
  authState.staffMembership = null;
  authState.refresh = vi.fn(async () => undefined);
  authState.signOut = vi.fn(async () => undefined);
  tokenStore.set("access-token");
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  tokenStore.clear();
  vi.restoreAllMocks();
});

describe("StaffInvitationPage", () => {
  it("redirects anonymous users to login with next", async () => {
    authState.status = "unauthenticated";
    globalThis.fetch = vi.fn(async () => jsonResponse(200, invitation)) as typeof fetch;

    renderPage("/staff/invitations/token-123?utm=email");

    expect(await screen.findByText("LOGIN")).toBeInTheDocument();
  });

  it("accepts the invitation, refreshes CurrentUser and navigates to cabinet", async () => {
    const fetchSpy = vi.fn(async (input: RequestInfo | URL) => {
      const url = urlOf(input);
      if (url.includes("/staff/invitations/accept")) {
        return jsonResponse(201, {
          data: { role: "DIRECTOR", status: "ACTIVE", organizationId: "org-1" },
        });
      }
      if (url.includes("/staff/invitations/token-123")) {
        return jsonResponse(200, invitation);
      }
      return problem(404);
    });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const queryClient = renderPage();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await screen.findByText("Взлёт талантов");
    await userEvent.click(screen.getByRole("button", { name: /Accept invitation/i }));

    await screen.findByText("Панель кабинета");
    expect(authState.refresh).toHaveBeenCalledTimes(1);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["identity", "current-user"] });
  });

  it("renders expired invitation", async () => {
    globalThis.fetch = vi.fn(async () => problem(410)) as typeof fetch;

    renderPage();

    expect(await screen.findByText("Срок действия приглашения истек.")).toBeInTheDocument();
  });

  it("renders invalid invitation", async () => {
    globalThis.fetch = vi.fn(async () => problem(404)) as typeof fetch;

    renderPage();

    expect(await screen.findByText("Приглашение не найдено.")).toBeInTheDocument();
  });

  it("renders already accepted with cabinet action for staff users", async () => {
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    globalThis.fetch = vi.fn(async () => problem(409)) as typeof fetch;

    renderPage();

    expect(await screen.findByText("Приглашение уже использовано.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Перейти в кабинет" })).toHaveAttribute(
      "href",
      "/cabinet",
    );
  });

  it("renders wrong account actions on 403 accept", async () => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = urlOf(input);
      if (url.includes("/staff/invitations/accept")) return problem(403);
      return jsonResponse(200, invitation);
    }) as typeof fetch;

    renderPage();
    await screen.findByText("Взлёт талантов");
    await userEvent.click(screen.getByRole("button", { name: /Accept invitation/i }));

    expect(await screen.findByText("Вы вошли под другой учетной записью.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Switch account" })).toBeInTheDocument();
  });
});
