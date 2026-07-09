import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";

export interface StaffInvitationDetails {
  organizationName: string;
  role: StaffInvitationRole;
  expiresAt: string;
  invitedEmail: string;
}

export type StaffInvitationRole =
  | "OWNER"
  | "DIRECTOR"
  | "FINANCE"
  | "COMPETITION_MANAGER"
  | "CONTENT_MANAGER"
  | "MODERATOR"
  | "SUPPORT";

export interface AcceptedStaffMembership {
  role: StaffInvitationRole;
  status: "PENDING" | "ACTIVE" | "REVOKED";
  organizationId: string;
}

export interface AcceptStaffInvitationResponse {
  data: AcceptedStaffMembership;
  meta?: { requestId?: string };
}

export const staffInvitationKeys = {
  detail: (token: string) => ["organization", "staff-invitation", token] as const,
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    return await apiClient(path, options).json<T>();
  } catch (error) {
    throw await toApiError(error);
  }
}

export async function fetchStaffInvitation(token: string): Promise<StaffInvitationDetails> {
  return request<StaffInvitationDetails>(`staff/invitations/${encodeURIComponent(token)}`);
}

export async function acceptStaffInvitation(token: string): Promise<AcceptStaffInvitationResponse> {
  return request<AcceptStaffInvitationResponse>("staff/invitations/accept", {
    method: "POST",
    json: { token },
  } as RequestInit & { json: { token: string } });
}

export function useStaffInvitation(
  token: string | undefined,
): UseQueryResult<StaffInvitationDetails, ApiError> {
  return useQuery<StaffInvitationDetails, ApiError>({
    queryKey: staffInvitationKeys.detail(token ?? ""),
    queryFn: () => fetchStaffInvitation(token ?? ""),
    enabled: Boolean(token),
    retry: false,
  });
}

export function useAcceptStaffInvitation(): UseMutationResult<
  AcceptStaffInvitationResponse,
  ApiError,
  string
> {
  return useMutation<AcceptStaffInvitationResponse, ApiError, string>({
    mutationFn: acceptStaffInvitation,
  });
}
