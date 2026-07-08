import type { Decorator, Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { VerifyEmailPage } from "./index";

/**
 * Verify-email is a single route with three states driven by the `?token=`
 * query param and the confirmation outcome. Each story sets the URL and stubs
 * `fetch` accordingly, wrapped in a fresh QueryClient (no retries) + router.
 */
function withRoute(url: string): Decorator {
  return (Story) => (
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <MemoryRouter initialEntries={[url]}>
        <div className="w-full max-w-sm">
          <Story />
        </div>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const meta = {
  title: "Pages/Auth/VerifyEmail",
  component: VerifyEmailPage,
  parameters: { layout: "centered" },
} satisfies Meta<typeof VerifyEmailPage>;

export default meta;

type Story = StoryObj<typeof meta>;

/** Confirmation in flight (never resolves) — the verifying spinner. */
export const Verifying: Story = {
  decorators: [withRoute("/verify-email?token=abc")],
  beforeEach: () => {
    globalThis.fetch = (() => new Promise<Response>(() => undefined)) as typeof fetch;
  },
};

/** The token was accepted — the success state. */
export const Success: Story = {
  decorators: [withRoute("/verify-email?token=abc")],
  beforeEach: () => {
    globalThis.fetch = (async () =>
      jsonResponse(200, {
        data: {
          id: "1",
          type: "user",
          email: "u@e.com",
          displayName: "U",
          emailVerified: true,
          status: "active",
        },
      })) as typeof fetch;
  },
};

/** The token expired (410) — the failed state with a tailored message. */
export const Expired: Story = {
  decorators: [withRoute("/verify-email?token=abc")],
  beforeEach: () => {
    globalThis.fetch = (async () =>
      jsonResponse(410, {
        type: "https://api.vzlyot-talantov.ru/problems/token-expired",
        title: "Verification token expired",
        status: 410,
        code: "email-verification-expired",
      })) as typeof fetch;
  },
};

/** No token in the link — the failed state. */
export const MissingToken: Story = {
  decorators: [withRoute("/verify-email")],
};
