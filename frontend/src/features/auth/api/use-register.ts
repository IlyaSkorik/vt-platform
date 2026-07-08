import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { DEFAULT_LOCALE } from "@/shared/api";
import { registerAccount } from "@/shared/api/generated/identity/identity";
import type { User } from "@/shared/api/generated/model";
import type { RegisterValues } from "../model/schemas";

/** The terms version the client presents for acceptance (API-001 §4.1, IDN-010). */
export const CURRENT_TERMS_VERSION = "2026-01";

/**
 * Registration mutation (`POST /auth/registration`, API-001 §4.1).
 *
 * Creates an adult account and triggers email verification. Returns the created
 * {@link User} (status `registered`, `emailVerified: false`) so the page can
 * route to the "check your inbox" state. An `Idempotency-Key` makes the create
 * safely retryable (API-000 §19).
 */
export function useRegister(): UseMutationResult<User, ApiError, RegisterValues> {
  return useMutation<User, ApiError, RegisterValues>({
    mutationFn: async ({ displayName, email, password }) => {
      const response = await registerAccount(
        {
          displayName,
          email,
          password,
          locale: DEFAULT_LOCALE,
          acceptedTermsVersion: CURRENT_TERMS_VERSION,
        },
        { headers: { "Idempotency-Key": crypto.randomUUID() } },
      );
      if (response.status !== 201) {
        throw new Error("Unexpected response while registering the account.");
      }
      return response.data.data;
    },
  });
}
