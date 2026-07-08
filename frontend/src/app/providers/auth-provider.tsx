import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, use, useCallback, useEffect, useMemo, useState } from "react";
import { authKeys, fetchCurrentUser } from "@/features/auth";
import { onSessionEvent, refreshAccessToken, tokenStore } from "@/shared/api";
import { deleteCurrentSession } from "@/shared/api/generated/identity/identity";
import type { User } from "@/shared/api/generated/model";

/** The authenticated user, sourced from `GET /users/me` (API-001 §4.8). */
export type AuthUser = User;

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  isAuthenticated: boolean;
  /**
   * True when a previously live session dropped (expired token + failed
   * refresh, or reuse detection). Lets guards route to `/session-expired`
   * instead of the plain login screen.
   */
  sessionExpired: boolean;
  /**
   * Re-derive the session from the server. Called after a successful login (the
   * form already set the access token) and available for manual refresh.
   */
  refresh: () => Promise<void>;
  /** Revoke the session (`DELETE /auth/sessions/current`) and clear local state. */
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Auth provider — owns the session lifecycle.
 *
 * Sits inside the QueryClientProvider so it can drive TanStack Query directly.
 * The current-user query is the single source of truth: its data means an
 * authenticated session, its absence means none.
 *
 * Cold-start bootstrap is proactive (no wasted 401):
 *   - Access token already in memory → enable `GET /users/me` straight away.
 *   - No token → attempt one silent `POST /auth/token/refresh` (shared
 *     single-flight). The httpOnly refresh cookie is the sole source of truth
 *     for whether a session exists, so we always ask the server: on success the
 *     fresh token is stored and the query is enabled; on 401 we settle anonymous
 *     without ever firing a `GET /users/me` that we know would 401.
 *
 * Refresh-on-401 remains as the runtime safety net (expired/revoked token mid
 * session). A `session-expired` event from the transport (failed refresh) flips
 * the flag that routes guards to the dedicated screen.
 */
export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const query = useQuery<AuthUser>({
    queryKey: authKeys.currentUser,
    queryFn: ({ signal }) => fetchCurrentUser(signal),
    enabled,
    retry: false,
    staleTime: 5 * 60_000,
  });

  // Proactive session restoration, exactly once on mount.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      // A token in memory (e.g. just after login) → fetch /me directly.
      // Otherwise ask the server via the refresh cookie: it alone decides
      // whether a session exists. Either outcome settles bootstrap.
      const restored = tokenStore.get() !== null || (await refreshAccessToken());
      if (!cancelled) {
        setEnabled(restored);
        setBootstrapping(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = useCallback(async () => {
    setSessionExpired(false);
    setEnabled(true);
    await queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
  }, [queryClient]);

  const logout = useMutation({
    mutationFn: async () => {
      try {
        await deleteCurrentSession();
      } finally {
        tokenStore.clear();
      }
    },
  });

  const signOut = useCallback(async () => {
    await logout.mutateAsync().catch(() => undefined);
    setEnabled(false);
    setSessionExpired(false);
    queryClient.setQueryData(authKeys.currentUser, null);
    await queryClient.clear();
  }, [logout, queryClient]);

  // React to a transport-level session drop (failed silent refresh).
  useEffect(() => {
    return onSessionEvent("session-expired", () => {
      const wasAuthenticated = queryClient.getQueryData(authKeys.currentUser) != null;
      tokenStore.clear();
      queryClient.setQueryData(authKeys.currentUser, null);
      setEnabled(false);
      setSessionExpired(wasAuthenticated);
    });
  }, [queryClient]);

  const user = query.data ?? null;

  const status: AuthStatus = useMemo(() => {
    if (bootstrapping || (enabled && query.isLoading)) {
      return "loading";
    }
    return user ? "authenticated" : "unauthenticated";
  }, [bootstrapping, enabled, query.isLoading, user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      isAuthenticated: status === "authenticated",
      sessionExpired,
      refresh,
      signOut,
    }),
    [status, user, sessionExpired, refresh, signOut],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

/** Access the auth session. Must be used within `AuthProvider`. */
export function useAuth(): AuthContextValue {
  const context = use(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
