import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { requestPasswordReset } from "@/shared/api/generated/identity/identity";
import type { ForgotPasswordValues } from "../model/schemas";

/**
 * Password-reset request (`POST /auth/password-reset/requests`, API-001 §4.7).
 *
 * Always resolves with `202` whether or not the email exists — the server does
 * not reveal account existence (no user enumeration, API-000 §26). The UI shows
 * the same "if an account exists, we've sent a link" confirmation regardless.
 */
export function useForgotPassword(): UseMutationResult<void, ApiError, ForgotPasswordValues> {
  return useMutation<void, ApiError, ForgotPasswordValues>({
    mutationFn: async ({ email }) => {
      await requestPasswordReset({ email });
    },
  });
}
