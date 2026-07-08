import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { tokenStore } from "@/shared/api";
import { LoginForm } from "./login-form";

/** Render the form inside the providers it depends on (Query + Router). */
function renderForm(onSuccess = vi.fn()): { onSuccess: ReturnType<typeof vi.fn> } {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  render(<LoginForm onSuccess={onSuccess} />, { wrapper });
  return { onSuccess };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  tokenStore.clear();
  vi.restoreAllMocks();
});

describe("LoginForm", () => {
  beforeEach(() => {
    tokenStore.clear();
  });

  it("shows client validation errors on empty submit and does not call the API", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Войти" }));

    expect(await screen.findByText("Укажите email")).toBeInTheDocument();
    expect(screen.getByText("Укажите пароль")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("submits valid credentials, stores the token, and calls onSuccess", async () => {
    globalThis.fetch = vi.fn(async () =>
      jsonResponse(201, {
        data: {
          type: "session",
          accessToken: "access-123",
          tokenType: "Bearer",
          expiresIn: 900,
          user: { id: "1", type: "user", email: "user@example.com", displayName: "User" },
        },
      }),
    ) as unknown as typeof fetch;
    const user = userEvent.setup();
    const { onSuccess } = renderForm();

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Пароль"), "password123");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(tokenStore.get()).toBe("access-123");
  });

  it("renders a form-level error alert when the server rejects credentials", async () => {
    globalThis.fetch = vi.fn(async () =>
      jsonResponse(401, {
        type: "https://api.vzlyot-talantov.ru/problems/authentication-failed",
        title: "Authentication failed",
        status: 401,
        detail: "Неверный email или пароль.",
      }),
    ) as unknown as typeof fetch;
    const user = userEvent.setup();
    const { onSuccess } = renderForm();

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Пароль"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Неверный email или пароль.");
    expect(onSuccess).not.toHaveBeenCalled();
    expect(tokenStore.get()).toBeNull();
  });
});
