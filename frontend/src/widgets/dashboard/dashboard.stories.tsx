import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { AuthProvider } from "@/app/providers";
import { authKeys } from "@/features/auth";
import { tokenStore } from "@/shared/api";
import type { User } from "@/shared/api/generated/model";
import { Dashboard } from "./dashboard";

/**
 * The composed dashboard. It reads the session via `useAuth`, so the decorator
 * seeds an authenticated current-user directly into the query cache (and a
 * token so the provider treats the session as live) — no network needed. The
 * widget queries resolve against their in-repo mocks.
 */
const DEMO_USER: User = {
  id: "u-1",
  type: "user",
  email: "maria@vzlettalantov.by",
  displayName: "Мария",
  status: "active",
  emailVerified: true,
};

const meta = {
  title: "Dashboard/Dashboard",
  component: Dashboard,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => {
      const client = new QueryClient({
        defaultOptions: { queries: { retry: false, staleTime: 5 * 60_000 } },
      });
      client.setQueryData(authKeys.currentUser, DEMO_USER);
      tokenStore.set("story-access-token");
      return (
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <AuthProvider>
              <div className="p-4 md:p-6 lg:p-8">
                <Story />
              </div>
            </AuthProvider>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof Dashboard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
