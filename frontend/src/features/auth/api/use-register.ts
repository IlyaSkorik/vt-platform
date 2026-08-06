import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { DEFAULT_LOCALE } from "@/shared/api";
import { registerAccount } from "@/shared/api/generated/identity/identity";
import type { User } from "@/shared/api/generated/model";
import { ACCOUNT_CONSENTS } from "@/shared/consents";
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
    mutationFn: async ({
      firstName,
      lastName,
      email,
      password,
      acceptTerms,
      acceptDataProcessing,
      acceptMarketing,
    }) => {
      const response = await registerAccount(
        {
          firstName,
          lastName,
          email,
          password,
          locale: DEFAULT_LOCALE,
          // Sent with the account, not after it: an account whose consents were
          // recorded by a second request that failed would be an account processing
          // data with no recorded basis (LEGAL-001 §13.3).
          consents: acceptedAccountConsents({ acceptTerms, acceptDataProcessing, acceptMarketing }),
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

/**
 * The consents to record, as `(code, version)` pairs read from the catalogue.
 *
 * A definition may stand for more than one journal entry (the terms box records both
 * the terms and the policy acknowledgement), so the codes come from the catalogue
 * rather than being listed again here.
 */
function acceptedAccountConsents(accepted: {
  acceptTerms: boolean;
  acceptDataProcessing: boolean;
  acceptMarketing: boolean;
}): { consentType: string; version: string }[] {
  const ticked: Record<string, boolean> = {
    terms_of_service: accepted.acceptTerms,
    data_processing: accepted.acceptDataProcessing,
    marketing: accepted.acceptMarketing,
  };
  return ACCOUNT_CONSENTS.filter((consent) => ticked[consent.code] === true).flatMap((consent) =>
    (consent.records ?? [consent.code]).map((code) => ({
      consentType: code,
      version: consent.version,
    })),
  );
}
