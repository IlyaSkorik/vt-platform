import { type UseMutationResult, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { actingOrganizationStore, tokenStore } from "@/shared/api";
import { deleteCurrentSession } from "@/shared/api/generated/identity/identity";
import { authKeys } from "./current-user";

/**
 * Logout mutation (`DELETE /auth/sessions/current`, API-001 §4.6).
 *
 * Revokes the current session and its refresh-token family server-side (the
 * refresh cookie is cleared), then drops the in-memory access token and clears
 * cached server state. Local teardown runs even if the network call fails, so
 * the client never keeps a session the user asked to end.
 */
export function useLogout(): UseMutationResult<void, ApiError, void> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, void>({
    mutationFn: async () => {
      try {
        await deleteCurrentSession();
      } finally {
        tokenStore.clear();
      }
    },
    onSettled: async () => {
      // Вместе с сессией кончается и кабинет, в который оператор заходил.
      actingOrganizationStore.set(null);
      queryClient.setQueryData(authKeys.currentUser, null);
      await queryClient.clear();
    },
  });
}
