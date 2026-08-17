import { describe, expect, it } from "vitest";
import { isStaffWorkspaceRoute } from "./navigation";

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
