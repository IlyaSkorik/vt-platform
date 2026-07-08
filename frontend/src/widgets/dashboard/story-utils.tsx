import type { Decorator } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

/**
 * Storybook helpers for the dashboard widgets.
 *
 * Presentational `*View` components are pure and need no providers, but the
 * connected widgets (and any card containing a router `Link`) require a
 * QueryClient + Router. This decorator supplies both with retries disabled so
 * network-driven states resolve deterministically in the canvas.
 */
function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

/** Base decorator: fresh QueryClient + in-memory router. */
export const withDashboardProviders: Decorator = (Story) => (
  <QueryClientProvider client={makeClient()}>
    <MemoryRouter>
      <Story />
    </MemoryRouter>
  </QueryClientProvider>
);

/** Constrain a widget to a realistic side-column width for review. */
export const withCardWidth: Decorator = (Story) => (
  <div className="w-full max-w-md">
    <Story />
  </div>
);
