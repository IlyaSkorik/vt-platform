import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { confirmPasswordReset } from "@/shared/api/generated/identity/identity";
import type { ResetPasswordValues } from "../model/schemas";

/**
 * Password-reset confirmation (`POST /auth/password-reset/confirmations`,
 * API-001 §4.7). Sets a new password using the emailed token and revokes all
 * sessions; the user must sign in again. A `410` means the token expired, a
 * `422` a weak/breached password — both surfaced via Problem Details.
 */
export function useResetPassword(): UseMutationResult<void, ApiError, ResetPasswordValues> {
  return useMutation<void, ApiError, ResetPasswordValues>({
    mutationFn: async ({ token, password }) => {
      await confirmPasswordReset({ token, newPassword: password });
    },
  });
}
