import { describe, expect, it } from "vitest";
import type { AuthModule } from "@/app/providers";
import { ROUTES } from "@/shared/config";
import { isStaffWorkspaceRoute, visibleStaffNavigation } from "./navigation";

describe("isStaffWorkspaceRoute", () => {
  it("counts the screens worked in rather than passed through", () => {
    expect(isStaffWorkspaceRoute("/staff/competitions/01900000-0000-7000-8000-000000000001")).toBe(
      true,
    );
    expect(
      isStaffWorkspaceRoute(
        "/staff/diplomas/templates/01900000-0000-7000-8000-0000000000aa/constructor",
      ),
    ).toBe(true);
    expect(isStaffWorkspaceRoute("/staff/program")).toBe(true);
    expect(isStaffWorkspaceRoute("/staff/applications")).toBe(true);
  });

  it("leaves ordinary pages alone", () => {
    expect(isStaffWorkspaceRoute("/staff")).toBe(false);
    expect(isStaffWorkspaceRoute("/staff/competitions")).toBe(false);
    expect(isStaffWorkspaceRoute("/staff/competitions/new")).toBe(false);
    expect(isStaffWorkspaceRoute("/staff/diplomas")).toBe(false);
    expect(isStaffWorkspaceRoute("/staff/participants")).toBe(false);
    expect(isStaffWorkspaceRoute("/staff/organization")).toBe(false);
  });
});

describe("visibleStaffNavigation", () => {
  const paths = (modules: AuthModule[], options?: { isPlatformAdmin?: boolean }) =>
    visibleStaffNavigation(modules, options).map((item) => item.path);

  it("offers an organization that holds one module only that module", () => {
    const offered = paths(["VOTING"]);

    expect(offered).not.toContain(ROUTES.staffCompetitions);
    expect(offered).not.toContain(ROUTES.staffDiplomas);
    expect(offered).not.toContain(ROUTES.staffFinance);
  });

  it("always keeps the sections an organization cannot exist without", () => {
    const offered = paths([]);

    expect(offered).toContain(ROUTES.staff);
    expect(offered).toContain(ROUTES.staffOrganization);
    expect(offered).toContain(ROUTES.staffUsers);
    expect(offered).toContain(ROUTES.staffInvitations);
    expect(offered).toContain(ROUTES.staffSettings);
  });

  it("shows a module's section once it is connected", () => {
    expect(paths(["DIPLOMAS"])).toContain(ROUTES.staffDiplomas);
  });

  it("shows the platform operator everything — they are staff of no organization", () => {
    expect(paths([], { isPlatformAdmin: true })).toContain(ROUTES.staffFinance);
  });
});
