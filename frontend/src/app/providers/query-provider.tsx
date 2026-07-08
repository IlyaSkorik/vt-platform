import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";
import { createQueryClient } from "@/shared/api";
import { env } from "@/shared/config";

/**
 * TanStack Query provider.
 *
 * The QueryClient is created once per app instance via `useState` (never at
 * module scope) so tests and any future SSR/hydration get an isolated cache.
 * Devtools are mounted in development only.
 */
export function QueryProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {env.isDev ? <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" /> : null}
    </QueryClientProvider>
  );
}
