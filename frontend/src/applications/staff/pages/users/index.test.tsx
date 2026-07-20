import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type StaffMember,
  useChangeStaffRole,
  useRevokeStaffMember,
  useStaffMembers,
} from "@/features/staff-members";
import { StaffUsersPage } from "./index";

vi.mock("@/features/staff-members", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/staff-members")>()),
  useStaffMembers: vi.fn(),
  useChangeStaffRole: vi.fn(),
  useRevokeStaffMember: vi.fn(),
}));

vi.mock("@/app/providers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/providers")>()),
  useAuth: vi.fn(),
}));

const { useAuth } = await import("@/app/providers");

const mockedList = vi.mocked(useStaffMembers);
const mockedChange = vi.mocked(useChangeStaffRole);
const mockedRevoke = vi.mocked(useRevokeStaffMember);
const mockedAuth = vi.mocked(useAuth);

function aMember(overrides: Partial<StaffMember> = {}): StaffMember {
  return {
    id: "01900000-0000-7000-8000-0000000000aa",
    userId: "user-1",
    email: "member@example.com",
    displayName: "Иван Иванов",
    role: "SUPPORT",
    status: "ACTIVE",
    invitedAt: null,
    acceptedAt: "2026-08-01T10:00:00Z",
    createdAt: "2026-08-01T10:00:00Z",
    ...overrides,
  };
}

function setAuthRole(role: "OWNER" | "SUPPORT"): void {
  mockedAuth.mockReturnValue({
    staffMembership: { role, status: "ACTIVE" },
  } as unknown as ReturnType<typeof useAuth>);
}

function stubMutations(): { revoke: ReturnType<typeof vi.fn> } {
  const revoke = vi.fn().mockResolvedValue(undefined);
  mockedChange.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue(undefined),
    isPending: false,
  } as unknown as ReturnType<typeof useChangeStaffRole>);
  mockedRevoke.mockReturnValue({
    mutateAsync: revoke,
    isPending: false,
  } as unknown as ReturnType<typeof useRevokeStaffMember>);
  return { revoke };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("StaffUsersPage", () => {
  it("renders members with name, email and status", () => {
    setAuthRole("OWNER");
    stubMutations();
    mockedList.mockReturnValue({
      data: [aMember()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStaffMembers>);

    render(<StaffUsersPage />);

    expect(screen.getByText("Иван Иванов")).toBeInTheDocument();
    expect(screen.getByText("member@example.com")).toBeInTheDocument();
    expect(screen.getByText("Активен")).toBeInTheDocument();
  });

  it("lets an admin revoke access", async () => {
    setAuthRole("OWNER");
    const { revoke } = stubMutations();
    mockedList.mockReturnValue({
      data: [aMember()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStaffMembers>);

    render(<StaffUsersPage />);

    await userEvent.click(screen.getByRole("button", { name: /отозвать доступ/i }));
    expect(revoke).toHaveBeenCalledWith("01900000-0000-7000-8000-0000000000aa");
  });

  it("shows a plain role label and no actions to non-admin staff", () => {
    setAuthRole("SUPPORT");
    stubMutations();
    mockedList.mockReturnValue({
      data: [aMember({ role: "MODERATOR" })],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStaffMembers>);

    render(<StaffUsersPage />);

    expect(screen.getByText("Модератор")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /отозвать доступ/i })).not.toBeInTheDocument();
    // No role <combobox> for non-admins.
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});
