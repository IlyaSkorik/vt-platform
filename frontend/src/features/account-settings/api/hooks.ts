import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

/**
 * The account's own settings — `PUT /users/me/{password,email,phone}`.
 *
 * Written directly against the shared transport rather than generated: these
 * endpoints live under the Identity tag, whose client is generated from the
 * committed `openapi/schema.yaml` subset, and three one-line calls are not worth
 * regenerating that surface for. The shape is the platform's usual envelope.
 */

/** Every one of these answers with the account as it now stands. */
interface AccountEnvelope {
  data: {
    id: string;
    email: string;
    displayName: string;
    emailVerified: boolean;
    phone: string | null;
    phoneVerified: boolean;
  };
}

async function put<TBody>(path: string, json: TBody): Promise<AccountEnvelope["data"]> {
  try {
    return (await apiClient(path, { method: "put", json }).json<AccountEnvelope>()).data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export type ChangePasswordInput = { currentPassword: string; newPassword: string };
export type ChangeEmailInput = { email: string; currentPassword: string };
export type ChangePhoneInput = { phone: string };

/**
 * Replace the password. The session survives — the server does not revoke it,
 * because the person who typed the current password is the one sitting here.
 */
export function useChangePassword(): UseMutationResult<
  AccountEnvelope["data"],
  ApiError,
  ChangePasswordInput
> {
  return useMutation({ mutationFn: (input) => put("users/me/password", input) });
}

/** Move the account to another address; the new one starts unverified. */
export function useChangeEmail(): UseMutationResult<
  AccountEnvelope["data"],
  ApiError,
  ChangeEmailInput
> {
  return useMutation({ mutationFn: (input) => put("users/me/email", input) });
}

/** Set or replace the phone number an organizer can reach the applicant on. */
export function useChangePhone(): UseMutationResult<
  AccountEnvelope["data"],
  ApiError,
  ChangePhoneInput
> {
  return useMutation({ mutationFn: (input) => put("users/me/phone", input) });
}

// ---------------------------------------------------------------------------
// Consents
// ---------------------------------------------------------------------------

/** One entry of the account's consent journal, as the settings screen reads it. */
export interface ConsentEntry {
  id: string;
  consentType: string;
  version: string;
  status: string;
  purpose: string | null;
  subjectParticipantId: string | null;
  grantedAt: string | null;
  withdrawnAt: string | null;
}

/** Query key for the journal, so a withdrawal can invalidate it. */
export const consentsQueryKey = ["account", "consents"] as const;

/**
 * The consents currently in force for this account.
 *
 * Only the active ones: the settings screen answers "what am I agreeing to right now?",
 * which is the question a person actually has. The superseded and withdrawn history is
 * available from the same endpoint with `history=true` and belongs in a data-subject
 * request, not on a settings page.
 */
export function useConsents(): UseQueryResult<ConsentEntry[], ApiError> {
  return useQuery<ConsentEntry[], ApiError>({
    queryKey: consentsQueryKey,
    queryFn: async () => {
      try {
        return (await apiClient("users/me/consents").json<{ data: ConsentEntry[] }>()).data;
      } catch (error) {
        throw await toApiError(error);
      }
    },
  });
}

/**
 * Withdraw one consent.
 *
 * Unconditional by law (art. 5 of Law No. 99-З: at any time, without giving reasons), so
 * there is no confirmation step to talk anybody out of it and nothing to justify. The
 * journal keeps the withdrawn entry; what disappears is the consent, not the record.
 */
export function useWithdrawConsent(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: async (consentType) => {
      try {
        await apiClient(`users/me/consents/${consentType}`, { method: "delete" });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: consentsQueryKey }),
  });
}

/** Give a consent that is currently not held — the other direction of the same control. */
export function useGrantConsent(): UseMutationResult<
  void,
  ApiError,
  { consentType: string; version: string }
> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { consentType: string; version: string }>({
    mutationFn: async (body) => {
      try {
        await apiClient("users/me/consents", { method: "post", json: body });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: consentsQueryKey }),
  });
}
