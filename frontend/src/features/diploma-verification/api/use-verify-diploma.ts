import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, toApiError } from "@/shared/api";
import { verifyDiploma } from "@/shared/api/generated/diploma-verification/diploma-verification";
import type { DiplomaVerificationEnvelope } from "@/shared/api/generated/model-diploma-verification";
import type { VerifiedDiploma } from "../lib/types";
import { diplomaVerificationKeys } from "./keys";

/** Unwrap the `{ data, meta }` envelope into the verified diploma view model. */
function unwrapDiploma(body: unknown): VerifiedDiploma {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as DiplomaVerificationEnvelope).data;
    if (nested != null && typeof nested === "object") {
      return nested;
    }
  }
  throw new Error("Unexpected diploma verification response shape.");
}

async function fetchVerifiedDiploma(
  verificationToken: string,
  signal?: AbortSignal,
): Promise<VerifiedDiploma> {
  try {
    const response = await verifyDiploma(verificationToken, signal ? { signal } : {});
    return unwrapDiploma(response.data);
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * Verify one diploma by the token from its printed QR code.
 *
 * Unauthenticated — whoever holds the paper can check it. The response is a frozen
 * snapshot, so it is cached for five minutes; the only field that ever changes is
 * the degree (and, with it, the official PDF), and a fresh scan is a fresh mount.
 * A 404 means the token matches no diploma, which is terminal — never retried, so
 * a forged code fails fast instead of looking like a flaky network.
 */
export function useVerifyDiploma(
  verificationToken: string | undefined,
): UseQueryResult<VerifiedDiploma, ApiError> {
  return useQuery<VerifiedDiploma, ApiError>({
    queryKey: diplomaVerificationKeys.byToken(verificationToken ?? ""),
    queryFn: ({ signal }) => fetchVerifiedDiploma(verificationToken as string, signal),
    enabled: Boolean(verificationToken),
    staleTime: 300_000,
    retry: (failureCount, error) => error.status !== 404 && failureCount < 2,
  });
}
