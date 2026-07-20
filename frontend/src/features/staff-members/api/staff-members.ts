import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { StaffInvitationRole } from "@/features/staff-invitations";
import { type ApiError, apiClient, toApiError } from "@/shared/api";

/** A staff membership's lifecycle status. */
export type StaffMemberStatus = "PENDING" | "ACTIVE" | "REVOKED";

/** A staff member row: the membership joined to its Identity user card. */
export interface StaffMember {
  id: string;
  userId: string;
  email: string | null;
  displayName: string | null;
  role: StaffInvitationRole;
  status: StaffMemberStatus;
  invitedAt: string | null;
  acceptedAt: string | null;
  createdAt: string;
}

/** The payload accepted by the change-role endpoint. */
export interface ChangeStaffRoleInput {
  membershipId: string;
  role: StaffInvitationRole;
}

interface ListEnvelope<T> {
  data: T[];
  meta?: { requestId?: string };
}

export const staffMemberKeys = {
  list: ["organization", "staff-members"] as const,
};

async function request<T>(path: string, options?: Parameters<typeof apiClient>[1]): Promise<T> {
  try {
    return await apiClient(path, options).json<T>();
  } catch (error) {
    throw await toApiError(error);
  }
}

export async function fetchStaffMembers(): Promise<StaffMember[]> {
  const body = await request<ListEnvelope<StaffMember>>("staff/members");
  return body.data;
}

export async function changeStaffRole(input: ChangeStaffRoleInput): Promise<void> {
  await request(`staff/members/${encodeURIComponent(input.membershipId)}`, {
    method: "PATCH",
    json: { role: input.role },
  } as RequestInit & { json: { role: StaffInvitationRole } });
}

export async function revokeStaffMember(membershipId: string): Promise<void> {
  await request(`staff/members/${encodeURIComponent(membershipId)}/revoke`, { method: "POST" });
}

export function useStaffMembers(): UseQueryResult<StaffMember[], ApiError> {
  return useQuery<StaffMember[], ApiError>({
    queryKey: staffMemberKeys.list,
    queryFn: fetchStaffMembers,
    staleTime: 30_000,
  });
}

export function useChangeStaffRole(): UseMutationResult<void, ApiError, ChangeStaffRoleInput> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, ChangeStaffRoleInput>({
    mutationFn: changeStaffRole,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: staffMemberKeys.list });
    },
  });
}

export function useRevokeStaffMember(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: revokeStaffMember,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: staffMemberKeys.list });
    },
  });
}
