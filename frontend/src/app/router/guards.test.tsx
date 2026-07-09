import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { AuthStatus } from "@/app/providers";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ProtectedRoute, StaffRoute } from "./guards";

const authState = {
  status: "unauthenticated" as AuthStatus,
  sessionExpired: false,
  staffMembership: null as null | { role: string; status: string },
};

vi.mock("@/app/providers", () => ({
  useAuth: () => ({
    status: authState.status,
    sessionExpired: authState.sessionExpired,
    staffMembership: authState.staffMembership,
  }),
}));

function renderProtected(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path={ROUTES.cabinet.slice(1)} element={<p>Кабинет</p>} />
        </Route>
        <Route path={ROUTES.login.slice(1)} element={<p>Экран входа</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderGuest(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<GuestRoute />}>
          <Route path={ROUTES.login.slice(1)} element={<p>Вход</p>} />
        </Route>
        <Route path={ROUTES.cabinet.slice(1)} element={<p>Экран кабинета</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderStaff(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<StaffRoute />}>
          <Route path={ROUTES.staff.slice(1)} element={<p>Staff workspace</p>} />
        </Route>
        <Route path={ROUTES.login.slice(1)} element={<p>Экран входа</p>} />
        <Route path={ROUTES.cabinet.slice(1)} element={<p>Экран кабинета</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("renders nothing while the session is loading", () => {
    authState.status = "loading";
    const { container } = renderProtected(ROUTES.cabinet);
    expect(container).toBeEmptyDOMElement();
  });

  it("redirects unauthenticated users to login", () => {
    authState.status = "unauthenticated";
    renderProtected(ROUTES.cabinet);
    expect(screen.getByText("Экран входа")).toBeInTheDocument();
  });

  it("renders the protected outlet when authenticated", () => {
    authState.status = "authenticated";
    renderProtected(ROUTES.cabinet);
    expect(screen.getByText("Кабинет")).toBeInTheDocument();
  });
});

describe("GuestRoute", () => {
  it("renders nothing while the session is loading", () => {
    authState.status = "loading";
    const { container } = renderGuest(ROUTES.login);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders guest screens when unauthenticated", () => {
    authState.status = "unauthenticated";
    renderGuest(ROUTES.login);
    expect(screen.getByText("Вход")).toBeInTheDocument();
  });

  it("redirects authenticated users to the cabinet", () => {
    authState.status = "authenticated";
    renderGuest(ROUTES.login);
    expect(screen.getByText("Экран кабинета")).toBeInTheDocument();
  });
});

describe("StaffRoute", () => {
  it("redirects anonymous users to login", () => {
    authState.status = "unauthenticated";
    authState.staffMembership = null;
    renderStaff(ROUTES.staff);
    expect(screen.getByText("Экран входа")).toBeInTheDocument();
  });

  it("redirects authenticated non-staff users to cabinet", () => {
    authState.status = "authenticated";
    authState.staffMembership = null;
    renderStaff(ROUTES.staff);
    expect(screen.getByText("Экран кабинета")).toBeInTheDocument();
  });

  it("renders staff workspace when CurrentUser has staffMembership", () => {
    authState.status = "authenticated";
    authState.staffMembership = { role: "DIRECTOR", status: "ACTIVE" };
    renderStaff(ROUTES.staff);
    expect(screen.getByText("Staff workspace")).toBeInTheDocument();
  });
});
