import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { requestEmailVerification } from "@/shared/api/generated/identity/identity";

/**
 * (Re)send an email-verification link (`POST /auth/email-verification/requests`,
 * API-001 §4.2).
 *
 * Public and anti-enumeration: always resolves with `202` whether or not the
 * address is registered (or already verified) — the server never reveals account
 * existence (API-000 §26). The UI shows the same "we've sent a link" confirmation
 * regardless. Reachable pre-login, so a user gated out by an unverified email can
 * still request a fresh link.
 */
export function useResendVerification(): UseMutationResult<void, ApiError, string> {
  return useMutation<void, ApiError, string>({
    mutationFn: async (email) => {
      await requestEmailVerification({ email });
    },
  });
}
