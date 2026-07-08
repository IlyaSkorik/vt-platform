import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { AuthStatus } from "@/app/providers";
import { ROUTES } from "@/shared/config";
import { GuestRoute, ProtectedRoute } from "./guards";

/**
 * The guards read auth status from `useAuth`. We mock the provider module so
 * each test can drive a specific session state without a real auth backend.
 */
const status = { current: "unauthenticated" as AuthStatus };
vi.mock("@/app/providers", () => ({
  useAuth: () => ({ status: status.current, sessionExpired: false }),
}));

/**
 * Renders `ProtectedRoute` guarding `/dashboard`. The redirect target
 * (`/login`) is a sibling, NOT a child of the guard — otherwise a redirect
 * would re-enter the guard and loop forever.
 */
function renderProtected(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path={ROUTES.dashboard} element={<p>Панель</p>} />
        </Route>
        <Route path={ROUTES.login} element={<p>Экран входа</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Renders `GuestRoute` guarding `/login`; `/dashboard` is the sibling target. */
function renderGuest(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<GuestRoute />}>
          <Route path={ROUTES.login} element={<p>Вход</p>} />
        </Route>
        <Route path={ROUTES.dashboard} element={<p>Экран панели</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("renders nothing while the session is loading", () => {
    status.current = "loading";
    const { container } = renderProtected(ROUTES.dashboard);
    expect(container).toBeEmptyDOMElement();
  });

  it("redirects unauthenticated users to login", () => {
    status.current = "unauthenticated";
    renderProtected(ROUTES.dashboard);
    expect(screen.getByText("Экран входа")).toBeInTheDocument();
  });

  it("renders the protected outlet when authenticated", () => {
    status.current = "authenticated";
    renderProtected(ROUTES.dashboard);
    expect(screen.getByText("Панель")).toBeInTheDocument();
  });
});

describe("GuestRoute", () => {
  it("renders nothing while the session is loading", () => {
    status.current = "loading";
    const { container } = renderGuest(ROUTES.login);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders guest screens when unauthenticated", () => {
    status.current = "unauthenticated";
    renderGuest(ROUTES.login);
    expect(screen.getByText("Вход")).toBeInTheDocument();
  });

  it("redirects authenticated users to the dashboard", () => {
    status.current = "authenticated";
    renderGuest(ROUTES.login);
    expect(screen.getByText("Экран панели")).toBeInTheDocument();
  });
});
