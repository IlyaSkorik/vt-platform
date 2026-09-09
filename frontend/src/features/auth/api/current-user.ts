import { getCurrentUser } from "@/shared/api/generated/identity/identity";
import type { CurrentUser } from "@/shared/api/generated/model";

/** Query keys for the Identity resources the auth feature reads. */
export const authKeys = {
  currentUser: ["identity", "current-user"] as const,
};

/**
 * Fetch the composed current user (`GET /users/me`), unwrapping the `data`
 * envelope so callers work with a plain {@link CurrentUser} — the Identity
 * account plus its Organization staff membership (`staffMembership` is null for
 * non-staff). Throws `ApiError` (incl. `401`) via the shared mutator, which
 * TanStack Query surfaces. The mutator rejects on any non-2xx, so only the
 * success branch reaches here — the status check narrows the response union.
 */
export async function fetchCurrentUser(signal?: AbortSignal): Promise<CurrentUser> {
  const response = await getCurrentUser(signal ? { signal } : {});
  if (response.status === 200) {
    return response.data.data;
  }
  throw new Error("Не удалось загрузить профиль. Попробуйте ещё раз.");
}
