import type { ReactNode } from "react";
import { AuthProvider } from "./auth-provider";
import { ErrorBoundary } from "./error-boundary";
import { QueryProvider } from "./query-provider";
import { ThemeProvider } from "./theme-provider";

/**
 * Composition root for all cross-cutting providers.
 *
 * Order matters (outermost first):
 *   ErrorBoundary → ThemeProvider → QueryProvider → AuthProvider
 *
 * - ErrorBoundary wraps everything so provider failures are contained.
 * - Theme is independent and cheap.
 * - Query sits above Auth because auth flows use the query client.
 */
export function AppProviders({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export { AuthProvider, type AuthStatus, type AuthUser, useAuth } from "./auth-provider";
export { ErrorBoundary } from "./error-boundary";
export { type ResolvedTheme, type Theme, ThemeProvider, useTheme } from "./theme-provider";
