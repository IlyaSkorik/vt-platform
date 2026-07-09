import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { AppShellLayout } from "./app-shell-layout";

const authState = {
  staffMembership: null as null | { role: string; status: string },
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
    isAuthenticated: true,
    sessionExpired: false,
    refresh: vi.fn(),
    signOut: vi.fn(),
  }),
}));

function renderShell(): void {
  render(
    <MemoryRouter initialEntries={["/cabinet"]}>
      <Routes>
        <Route element={<AppShellLayout />}>
          <Route path="/cabinet" element={<p>Кабинет</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("AppShellLayout staff navigation", () => {
  it("does not render staff dashboard navigation without staff membership", () => {
    authState.staffMembership = null;
    renderShell();

    expect(screen.queryByRole("link", { name: "Панель управления" })).not.toBeInTheDocument();
  });

  it("renders staff dashboard navigation from CurrentUser staffMembership", () => {
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    renderShell();

    expect(screen.getByRole("link", { name: "Панель управления" })).toHaveAttribute(
      "href",
      "/staff",
    );
  });
});
