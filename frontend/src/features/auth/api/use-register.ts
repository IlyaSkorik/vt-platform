import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { DEFAULT_LOCALE } from "@/shared/api";
import { registerAccount } from "@/shared/api/generated/identity/identity";
import type { User } from "@/shared/api/generated/model";
import type { RegisterValues } from "../model/schemas";

/**
 * Registration mutation (`POST /auth/registration`, API-001 §4.1).
 *
 * Creates an adult account and triggers email verification. Returns the created
 * {@link User} (status `registered`, `emailVerified: false`) so the page can
 * route to the "check your inbox" state. An `Idempotency-Key` makes the create
 * safely retryable (API-000 §19). The domain models a person's name as
 * structured parts, so the contract takes `firstName`/`lastName` and derives
 * the account's `displayName` from them.
 */
export function useRegister(): UseMutationResult<User, ApiError, RegisterValues> {
  return useMutation<User, ApiError, RegisterValues>({
    mutationFn: async ({ firstName, lastName, email, password }) => {
      const response = await registerAccount(
        {
          firstName,
          lastName,
          email,
          password,
          locale: DEFAULT_LOCALE,
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
