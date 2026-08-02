import { type UseMutationResult, useMutation } from "@tanstack/react-query";

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
