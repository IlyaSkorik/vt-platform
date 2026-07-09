import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { AuthProvider } from "@/app/providers";
import { authKeys } from "@/features/auth";
import { tokenStore } from "@/shared/api";
import type { CurrentUser } from "@/shared/api/generated/model";
import { Dashboard } from "./dashboard";

const DEMO_CURRENT_USER: CurrentUser = {
  user: {
    id: "u-1",
    type: "user",
    email: "maria@vzlettalantov.by",
    displayName: "Мария",
    status: "active",
    emailVerified: true,
  },
  staffMembership: null,
};

/**
 * Render the connected dashboard against a real (but network-free) stack: a
 * QueryClient seeded with an authenticated user + a token so `AuthProvider`
 * treats the session as live, wrapped in a router. The widget queries resolve
 * against their in-repo mocks, so `findBy*` waits for the real async path.
 */
function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 5 * 60_000 } },
  });
  client.setQueryData(authKeys.currentUser, DEMO_CURRENT_USER);
  tokenStore.set("test-access-token");

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  tokenStore.clear();
});

describe("Dashboard (integration)", () => {
  it("greets the authenticated user by name", () => {
    renderDashboard();
    expect(screen.getByRole("heading", { name: /Мария/ })).toBeInTheDocument();
  });

  it("renders the quick-action shortcuts immediately", () => {
    renderDashboard();
    expect(screen.getByRole("link", { name: /Создать конкурс/ })).toBeInTheDocument();
  });

  it("renders all widget regions", () => {
    renderDashboard();
    // Widget regions are labelled Cards; they exist even while their data loads.
    expect(screen.getByLabelText("Последние конкурсы")).toBeInTheDocument();
    expect(screen.getByLabelText("Последние заявки")).toBeInTheDocument();
    expect(screen.getByLabelText("Уведомления")).toBeInTheDocument();
    expect(screen.getByLabelText("Ближайшие события")).toBeInTheDocument();
    expect(screen.getByLabelText("Лента активности")).toBeInTheDocument();
  });

  it("resolves widget data from the mocked queries", async () => {
    renderDashboard();
    // Statistics tile value appears once the stats query settles.
    expect(await screen.findByText("1 284")).toBeInTheDocument();
    // A competition row appears once that query settles.
    expect(await screen.findByText("Весенний вокальный конкурс")).toBeInTheDocument();
    // An unread notifications badge appears once notifications settle.
    expect(await screen.findByLabelText("3 непрочитанных")).toBeInTheDocument();
  });
});
