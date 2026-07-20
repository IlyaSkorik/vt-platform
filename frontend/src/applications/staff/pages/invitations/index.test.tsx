import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type StaffInvitationSummary,
  useCreateStaffInvitation,
  useRevokeStaffInvitation,
  useStaffInvitations,
} from "@/features/staff-invitations";
import { StaffInvitationsPage } from "./index";

vi.mock("@/features/staff-invitations", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/staff-invitations")>()),
  useStaffInvitations: vi.fn(),
  useCreateStaffInvitation: vi.fn(),
  useRevokeStaffInvitation: vi.fn(),
}));

vi.mock("@/app/providers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/providers")>()),
  useAuth: vi.fn(),
}));

const { useAuth } = await import("@/app/providers");

const mockedList = vi.mocked(useStaffInvitations);
const mockedCreate = vi.mocked(useCreateStaffInvitation);
const mockedRevoke = vi.mocked(useRevokeStaffInvitation);
const mockedAuth = vi.mocked(useAuth);

function anInvitation(overrides: Partial<StaffInvitationSummary> = {}): StaffInvitationSummary {
  return {
    id: "01900000-0000-7000-8000-000000000001",
    organizationId: "org-1",
    email: "invitee@example.com",
    role: "MODERATOR",
    status: "pending",
    expiresAt: "2026-09-01T10:00:00Z",
    invitedBy: "user-1",
    acceptedAt: null,
    revokedAt: null,
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
  mockedCreate.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue(anInvitation()),
    isPending: false,
  } as unknown as ReturnType<typeof useCreateStaffInvitation>);
  mockedRevoke.mockReturnValue({
    mutateAsync: revoke,
    isPending: false,
  } as unknown as ReturnType<typeof useRevokeStaffInvitation>);
  return { revoke };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("StaffInvitationsPage", () => {
  it("renders the roster with a status badge and role label", () => {
    setAuthRole("OWNER");
    stubMutations();
    mockedList.mockReturnValue({
      data: [anInvitation()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStaffInvitations>);

    render(<StaffInvitationsPage />);

    // Scope to the table: the invite form's role <select> also lists role labels.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("invitee@example.com")).toBeInTheDocument();
    expect(table.getByText("Модератор")).toBeInTheDocument();
    expect(table.getByText("Ожидает")).toBeInTheDocument();
  });

  it("shows the invite form to admins and lets them revoke a pending invitation", async () => {
    setAuthRole("OWNER");
    const { revoke } = stubMutations();
    mockedList.mockReturnValue({
      data: [anInvitation()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStaffInvitations>);

    render(<StaffInvitationsPage />);

    expect(screen.getByRole("button", { name: /пригласить/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /отозвать/i }));
    expect(revoke).toHaveBeenCalledWith("01900000-0000-7000-8000-000000000001");
  });

  it("hides management controls from non-admin staff", () => {
    setAuthRole("SUPPORT");
    stubMutations();
    mockedList.mockReturnValue({
      data: [anInvitation()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStaffInvitations>);

    render(<StaffInvitationsPage />);

    expect(screen.queryByRole("button", { name: /пригласить/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /отозвать/i })).not.toBeInTheDocument();
  });

  it("surfaces a load error", () => {
    setAuthRole("OWNER");
    stubMutations();
    mockedList.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useStaffInvitations>);

    render(<StaffInvitationsPage />);

    expect(screen.getByText("Не удалось загрузить приглашения")).toBeInTheDocument();
  });
});
