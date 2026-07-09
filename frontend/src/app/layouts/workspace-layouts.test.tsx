import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ParticipantLayout } from "./participant-layout";
import { StaffLayout } from "./staff-layout";

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

function renderParticipant(): void {
  render(
    <MemoryRouter initialEntries={["/cabinet"]}>
      <Routes>
        <Route element={<ParticipantLayout />}>
          <Route path="/cabinet" element={<p>Личный контент</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
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

describe("workspace layouts", () => {
  beforeEach(() => {
    authState.staffMembership = null;
  });

  it("renders participant workspace without staff switcher for regular users", () => {
    renderParticipant();

    expect(screen.getByText("Личный контент")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Панель управления/ })).not.toBeInTheDocument();
  });

  it("renders participant workspace switcher from CurrentUser staffMembership", () => {
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    renderParticipant();

    expect(screen.getByRole("link", { name: /Личный кабинет/ })).toHaveAttribute(
      "href",
      "/cabinet",
    );
    expect(screen.getByRole("link", { name: /Панель управления/ })).toHaveAttribute(
      "href",
      "/staff",
    );
  });

  it("renders staff workspace in its dedicated layout", () => {
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    renderStaff();

    expect(screen.getByText("Staff content")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Навигация панели управления" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Личный кабинет/ })).toHaveAttribute(
      "href",
      "/cabinet",
    );
  });
});
