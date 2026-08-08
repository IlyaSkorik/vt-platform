import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ParticipantLayout } from "@/applications/participant/layouts/participant-layout";
import { PlatformLayout } from "@/applications/platform/layouts/platform-layout";
import { StaffLayout } from "@/applications/staff/layouts/staff-layout";

const authState = {
  staffMembership: null as null | { role: string; status: string },
  isPlatformAdmin: false,
};

vi.mock("@/app/providers", () => ({
  useTheme: () => ({
    resolvedTheme: "light",
    toggleTheme: vi.fn(),
  }),
  useAuth: () => ({
    status: "authenticated",
    user: { displayName: "Ирина", email: "staff@example.com" },
    staffMembership: authState.staffMembership,
    isStaff: authState.staffMembership?.status === "ACTIVE",
    isPlatformAdmin: authState.isPlatformAdmin,
    isAuthenticated: true,
    sessionExpired: false,
    refresh: vi.fn(),
    signOut: vi.fn(),
  }),
}));

/**
 * The cabinet shell fetches: its bell reads the notification feed to badge itself,
 * so the layout needs a QueryClient even though these tests are about navigation.
 * Retries are off — the request has nowhere to go here, and the bell renders its
 * unbadged state from no data, which is exactly what these tests want behind them.
 */
function renderParticipant(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/cabinet"]}>
        <Routes>
          <Route element={<ParticipantLayout />}>
            <Route path="/cabinet" element={<p>Личный контент</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderStaff(): void {
  render(
    <MemoryRouter initialEntries={["/staff"]}>
      <Routes>
        <Route element={<StaffLayout />}>
          <Route path="/staff" element={<p>Staff content</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

function getFirstWorkspaceSwitcher(): HTMLElement {
  const switcher = screen.getAllByRole("navigation", {
    name: "Переключение рабочего пространства",
  })[0];

  if (switcher == null) {
    throw new Error("Workspace switcher was not rendered");
  }

  return switcher;
}

function renderPlatform(): void {
  render(
    <MemoryRouter initialEntries={["/platform"]}>
      <Routes>
        <Route element={<PlatformLayout />}>
          <Route path="/platform" element={<p>Platform content</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("workspace layouts", () => {
  beforeEach(() => {
    authState.staffMembership = null;
    authState.isPlatformAdmin = false;
  });

  it("renders participant workspace without staff switcher for regular users", () => {
    renderParticipant();

    expect(screen.getByText("Личный контент")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Навигация личного кабинета" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Переключение рабочего пространства" }),
    ).not.toBeInTheDocument();
  });

  it("renders participant workspace switcher from CurrentUser staffMembership", () => {
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    renderParticipant();

    const switcher = getFirstWorkspaceSwitcher();
    expect(within(switcher).getByRole("link", { name: /Личный кабинет/ })).toHaveAttribute(
      "href",
      "/cabinet",
    );
    expect(within(switcher).getByRole("link", { name: /Панель управления/ })).toHaveAttribute(
      "href",
      "/staff",
    );
    expect(within(switcher).queryByRole("link", { name: /Платформа/ })).not.toBeInTheDocument();
  });

  it("offers the platform console to an operator who belongs to no organization", () => {
    // The grant is a command against an account, so this is the ordinary shape of a
    // platform operator — not an edge case. Gating the switcher on staff membership
    // used to leave them with no link into `/platform` at all.
    authState.isPlatformAdmin = true;
    renderParticipant();

    const switcher = getFirstWorkspaceSwitcher();
    expect(within(switcher).getByRole("link", { name: /Платформа/ })).toHaveAttribute(
      "href",
      "/platform",
    );
    // `/staff` would bounce straight back here without a membership, so it is not offered.
    expect(
      within(switcher).queryByRole("link", { name: /Панель управления/ }),
    ).not.toBeInTheDocument();
  });

  it("lets the platform shell switch back out", () => {
    authState.isPlatformAdmin = true;
    renderPlatform();

    expect(screen.getByText("Platform content")).toBeInTheDocument();
    const switcher = getFirstWorkspaceSwitcher();
    expect(within(switcher).getByRole("link", { name: /Личный кабинет/ })).toHaveAttribute(
      "href",
      "/cabinet",
    );
  });

  it("renders staff workspace in its dedicated layout", () => {
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    renderStaff();

    expect(screen.getByText("Staff content")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Навигация панели управления" }),
    ).toBeInTheDocument();

    const switcher = getFirstWorkspaceSwitcher();
    expect(within(switcher).getByRole("link", { name: /Личный кабинет/ })).toHaveAttribute(
      "href",
      "/cabinet",
    );
  });
});
