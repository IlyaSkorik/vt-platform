import { getCurrentUser } from "@/shared/api/generated/identity/identity";
import type { User } from "@/shared/api/generated/model";

/** Query keys for the Identity resources the auth feature reads. */
export const authKeys = {
  currentUser: ["identity", "current-user"] as const,
};

/**
 * Fetch the authenticated user (`GET /users/me`, API-001 §4.8), unwrapping the
 * `data` envelope so callers work with a plain {@link User}. Throws `ApiError`
 * (incl. `401`) via the shared mutator, which TanStack Query surfaces. The
 * mutator rejects on any non-2xx, so only the success branch reaches here — the
 * status check narrows the generated response union to that branch.
 */
export async function fetchCurrentUser(signal?: AbortSignal): Promise<User> {
  const response = await getCurrentUser(signal ? { signal } : {});
  if (response.status === 200) {
    return response.data.data;
  }
  throw new Error("Unexpected response for the current-user request.");
}
