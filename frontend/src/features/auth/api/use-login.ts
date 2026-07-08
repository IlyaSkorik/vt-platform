import { type UseMutationResult, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import { tokenStore } from "@/shared/api";
import { createSession } from "@/shared/api/generated/identity/identity";
import type { LoginValues } from "../model/schemas";
import { authKeys } from "./current-user";

/**
 * Login mutation (`POST /auth/sessions`, API-001 §4.4).
 *
 * On success the server sets the rotating refresh cookie (httpOnly) and returns
 * a short-lived access token, which we place in the in-memory {@link tokenStore}
 * — never localStorage. The refresh cookie is the sole source of truth for
 * session persistence; there is no client-side flag. The current-user query is
 * invalidated so the AuthProvider re-derives the session from `GET /users/me`.
 */
export function useLogin(): UseMutationResult<void, ApiError, LoginValues> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, LoginValues>({
    mutationFn: async ({ email, password }) => {
      const response = await createSession({ email, password });
      if (response.status !== 201) {
        throw new Error("Unexpected response while establishing the session.");
      }
      tokenStore.set(response.data.data.accessToken);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
    },
  });
}
