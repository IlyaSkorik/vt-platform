import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
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

/** Human-readable Russian labels for every staff role (shared across the panel). */
export const ROLE_LABELS: Record<StaffInvitationRole, string> = {
  OWNER: "Владелец",
  DIRECTOR: "Директор",
  FINANCE: "Финансы",
  COMPETITION_MANAGER: "Менеджер фестивалей",
  CONTENT_MANAGER: "Контент-менеджер",
  MODERATOR: "Модератор",
  SUPPORT: "Поддержка",
};

/** Role options for a `Select`, in the platform's canonical order. */
export const ROLE_OPTIONS: { value: StaffInvitationRole; label: string }[] = (
  Object.keys(ROLE_LABELS) as StaffInvitationRole[]
).map((role) => ({ value: role, label: ROLE_LABELS[role] }));

/** An invitation's lifecycle status, as derived by the roster read model. */
export type StaffInvitationStatus = "pending" | "accepted" | "revoked" | "expired";

/** A flat invitation row for the staff roster (never carries the token). */
export interface StaffInvitationSummary {
  id: string;
  organizationId: string;
  email: string;
  role: StaffInvitationRole;
  status: StaffInvitationStatus;
  expiresAt: string;
  invitedBy: string;
  acceptedAt: string | null;
  revokedAt: string | null;
  createdAt: string;
}

/** The payload accepted by the create-invitation endpoint. */
export interface CreateStaffInvitationInput {
  email: string;
  role: StaffInvitationRole;
}

interface ListEnvelope<T> {
  data: T[];
  meta?: { requestId?: string };
}

interface ItemEnvelope<T> {
  data: T;
  meta?: { requestId?: string };
}

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
  list: ["organization", "staff-invitations"] as const,
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

export async function fetchStaffInvitations(): Promise<StaffInvitationSummary[]> {
  const body = await request<ListEnvelope<StaffInvitationSummary>>("staff/invitations");
  return body.data;
}

export async function createStaffInvitation(
  input: CreateStaffInvitationInput,
): Promise<StaffInvitationSummary> {
  const body = await request<ItemEnvelope<StaffInvitationSummary>>("staff/invitations", {
    method: "POST",
    json: input,
  } as RequestInit & { json: CreateStaffInvitationInput });
  return body.data;
}

export async function revokeStaffInvitation(invitationId: string): Promise<StaffInvitationSummary> {
  const body = await request<ItemEnvelope<StaffInvitationSummary>>(
    `staff/invitations/${encodeURIComponent(invitationId)}/revoke`,
    { method: "POST" },
  );
  return body.data;
}

export function useStaffInvitations(): UseQueryResult<StaffInvitationSummary[], ApiError> {
  return useQuery<StaffInvitationSummary[], ApiError>({
    queryKey: staffInvitationKeys.list,
    queryFn: fetchStaffInvitations,
    staleTime: 30_000,
  });
}

export function useCreateStaffInvitation(): UseMutationResult<
  StaffInvitationSummary,
  ApiError,
  CreateStaffInvitationInput
> {
  const queryClient = useQueryClient();
  return useMutation<StaffInvitationSummary, ApiError, CreateStaffInvitationInput>({
    mutationFn: createStaffInvitation,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: staffInvitationKeys.list });
    },
  });
}

export function useRevokeStaffInvitation(): UseMutationResult<
  StaffInvitationSummary,
  ApiError,
  string
> {
  const queryClient = useQueryClient();
  return useMutation<StaffInvitationSummary, ApiError, string>({
    mutationFn: revokeStaffInvitation,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: staffInvitationKeys.list });
    },
  });
}
