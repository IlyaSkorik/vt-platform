import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { StaffLayout } from "./staff-layout";

// The chrome around the navigation owns its own data access; this suite is about the
// sidebar, so the header slots are stubbed out to keep the tree self-contained.
vi.mock("@/app/layouts/theme-toggle", () => ({ ThemeToggle: () => null }));
vi.mock("@/app/layouts/user-menu", () => ({ UserMenu: () => null }));
vi.mock("@/app/layouts/site-footer", () => ({ SiteFooter: () => null }));
vi.mock("@/applications/workspace-switcher", () => ({ WorkspaceSwitcher: () => null }));

// The sidebar shows the sections this organization holds, so it reads the session.
// These tests are about folding and unfolding it, not about entitlements, so the
// stub holds everything and the navigation renders in full.
vi.mock("@/app/providers", () => ({
  useAuth: () => ({
    enabledModules: [
      "COMPETITIONS",
      "APPLICATIONS",
      "PARTICIPANTS",
      "JURY",
      "PROGRAMS",
      "DIPLOMAS",
      "VOTING",
      "FINANCE",
      "ANALYTICS",
    ],
    isPlatformAdmin: false,
  }),
}));

const SIDEBAR = "Боковая навигация панели управления";
const WORKSPACE = "/staff/competitions/01900000-0000-7000-8000-000000000001";

function renderShell(at: string): void {
  render(
    <MemoryRouter initialEntries={[at]}>
      <Routes>
        <Route element={<StaffLayout />}>
          <Route path="/staff" element={<Link to={WORKSPACE}>Открыть фестиваль</Link>} />
          <Route
            path="/staff/competitions/:competitionId"
            element={<Link to="/staff">Назад</Link>}
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

function collapsed(): string | null {
  return screen.getByLabelText(SIDEBAR).getAttribute("data-collapsed");
}

describe("StaffLayout — the sidebar around a workspace", () => {
  it("keeps the navigation open on an ordinary page", () => {
    renderShell("/staff");

    expect(collapsed()).toBe("false");
  });

  it("opens a workspace with the navigation already folded away", () => {
    renderShell(WORKSPACE);

    expect(collapsed()).toBe("true");
  });

  it("folds it on the way in and brings it back on the way out", async () => {
    const user = userEvent.setup();
    renderShell("/staff");

    await user.click(screen.getByRole("link", { name: "Открыть фестиваль" }));
    expect(collapsed()).toBe("true");

    await user.click(screen.getByRole("link", { name: "Назад" }));
    expect(collapsed()).toBe("false");
  });

  it("leaves the choice with the staffer once they are inside", async () => {
    const user = userEvent.setup();
    renderShell(WORKSPACE);

    await user.click(screen.getByRole("button", { name: "Развернуть меню" }));

    expect(collapsed()).toBe("false");
  });
});
