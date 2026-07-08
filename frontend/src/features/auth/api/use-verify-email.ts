import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { confirmEmailVerification } from "@/shared/api/generated/identity/identity";
import type { User } from "@/shared/api/generated/model";

/**
 * Email-verification confirmation (`POST /auth/email-verification/confirmations`,
 * API-001 §4.2). The emailed token is the proof, so this needs no session.
 * Returns the now-verified {@link User}; a `410` means the token expired and a
 * fresh verification email is needed.
 */
export function useVerifyEmail(): UseMutationResult<User, ApiError, string> {
  return useMutation<User, ApiError, string>({
    mutationFn: async (token) => {
      const response = await confirmEmailVerification({ token });
      if (response.status !== 200) {
        throw new Error("Unexpected response while confirming the email.");
      }
      return response.data.data;
    },
  });
}
