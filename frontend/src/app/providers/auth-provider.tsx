import { createContext, use, useMemo } from "react";

/**
 * Authenticated user shape (placeholder).
 *
 * Deliberately minimal for bootstrap. The real model will be derived from
 * `GET /users/me` (API-001 §4.8) and its effective roles/scopes.
 */
export interface AuthUser {
  id: string;
  displayName: string;
  email: string;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  isAuthenticated: boolean;
  /** Establish a session. Wired to `POST /auth/sessions` by the Auth feature. */
  signIn: () => Promise<void>;
  /** Revoke the session. Wired to `DELETE /auth/sessions/current`. */
  signOut: () => Promise<void>;
}

const NOT_IMPLEMENTED = (): Promise<never> =>
  Promise.reject(new Error("Authentication is not implemented in the bootstrap foundation."));

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Auth provider — PLACEHOLDER.
 *
 * Establishes the context and public shape that route guards and the app
 * shell depend on, WITHOUT any authentication logic (no token exchange, no
 * refresh, no session persistence). It reports an unauthenticated session so
 * `ProtectedRoute`/`GuestRoute` behave correctly out of the box. The Auth
 * feature will replace the body with the real lifecycle (login, refresh via
 * the httpOnly cookie, logout) against the Identity API (API-001).
 */
export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const value = useMemo<AuthContextValue>(
    () => ({
      status: "unauthenticated",
      user: null,
      isAuthenticated: false,
      signIn: NOT_IMPLEMENTED,
      signOut: NOT_IMPLEMENTED,
    }),
    [],
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
