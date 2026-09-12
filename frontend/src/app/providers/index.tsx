import type { ReactNode } from "react";
import { Toaster } from "@/shared/ui";
import { AuthProvider } from "./auth-provider";
import { ErrorBoundary } from "./error-boundary";
import { QueryProvider } from "./query-provider";
import { ThemeProvider, useTheme } from "./theme-provider";

/**
 * The single Toaster mount, following the resolved theme.
 *
 * It has to exist for `toast()` to show anything at all: Sonner renders into this
 * one node, and without it every call across the app — "Сохранено", "Не удалось
 * загрузить PDF", every failure an operation reports — resolves quietly and the
 * user is told nothing.
 */
function AppToaster(): React.JSX.Element {
  const { resolvedTheme } = useTheme();
  return <Toaster theme={resolvedTheme} position="bottom-right" closeButton />;
}

/**
 * Composition root for all cross-cutting providers.
 *
 * Order matters (outermost first):
 *   ErrorBoundary → ThemeProvider → QueryProvider → AuthProvider
 *
 * - ErrorBoundary wraps everything so provider failures are contained.
 * - Theme is independent and cheap.
 * - Query sits above Auth because auth flows use the query client.
 *
 * The Toaster mounts here too, inside the theme: it is app-wide chrome rather than
 * any one screen's, and one mount is all Sonner wants.
 */
export function AppProviders({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>
            {children}
            <AppToaster />
          </AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export {
  type AuthModule,
  AuthProvider,
  type AuthStatus,
  type AuthUser,
  useAuth,
} from "./auth-provider";
export { ErrorBoundary } from "./error-boundary";
export { type ResolvedTheme, type Theme, ThemeProvider, useTheme } from "./theme-provider";
