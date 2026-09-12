import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { AuthStatus } from "@/app/providers";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ModuleRoute, ProtectedRoute, StaffRoute } from "./guards";

const authState = {
  status: "unauthenticated" as AuthStatus,
  sessionExpired: false,
  staffMembership: null as null | { role: string; status: string },
  isPlatformAdmin: false,
  enabledModules: [] as string[],
};

vi.mock("@/app/providers", () => ({
  useAuth: () => ({
    status: authState.status,
    sessionExpired: authState.sessionExpired,
    staffMembership: authState.staffMembership,
    isPlatformAdmin: authState.isPlatformAdmin,
    enabledModules: authState.enabledModules,
    hasModule: (module: string) => authState.enabledModules.includes(module),
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

function renderModule(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<ModuleRoute module="VOTING" />}>
          <Route path="staff/voting" element={<p>Голосования</p>} />
        </Route>
        <Route path={ROUTES.staff.slice(1)} element={<p>Панель управления</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ModuleRoute", () => {
  it("renders the section when the organization holds the module", () => {
    authState.status = "authenticated";
    authState.isPlatformAdmin = false;
    authState.enabledModules = ["VOTING"];

    renderModule("/staff/voting");

    expect(screen.getByText("Голосования")).toBeInTheDocument();
  });

  it("sends a staffer whose organization was not sold it back to the dashboard", () => {
    authState.status = "authenticated";
    authState.isPlatformAdmin = false;
    authState.enabledModules = ["PROGRAMS"];

    renderModule("/staff/voting");

    expect(screen.getByText("Панель управления")).toBeInTheDocument();
  });

  it("lets the platform operator through — they are staff of no organization", () => {
    authState.status = "authenticated";
    authState.isPlatformAdmin = true;
    authState.enabledModules = [];

    renderModule("/staff/voting");

    expect(screen.getByText("Голосования")).toBeInTheDocument();
  });

  it("renders nothing while the session is still loading", () => {
    authState.status = "loading";
    authState.isPlatformAdmin = false;
    authState.enabledModules = [];

    const { container } = renderModule("/staff/voting");

    expect(container).toBeEmptyDOMElement();
  });
});
