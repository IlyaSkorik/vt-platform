import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { type ReactNode, StrictMode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { VerifyEmailPage } from "./index";

/**
 * Render the page at a given URL inside the providers it depends on
 * (Query + Router). `strict` wraps in `StrictMode` to exercise React's
 * mount → unmount → remount, which the dispatch guard must survive.
 */
function renderPage(url: string, { strict = false }: { strict?: boolean } = {}): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const tree = (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>
        <VerifyEmailPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
  const wrapped = strict ? <StrictMode>{tree}</StrictMode> : tree;
  render(wrapped as ReactNode);
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const VERIFIED_USER = {
  data: {
    id: "018f9c2a-7e3b-7c21-9a1b-2c4e6f8a0d11",
    type: "user",
    email: "parent@example.com",
    displayName: "Ирина Смирнова",
    status: "active",
    emailVerified: true,
    phoneVerified: false,
    mfaEnabled: false,
    locale: "ru-RU",
    createdAt: "2026-07-08T00:00:00Z",
    updatedAt: "2026-07-08T00:00:00Z",
  },
};

function problem(status: number, extra: Record<string, unknown> = {}): Response {
  return jsonResponse(status, {
    type: "https://api.vzlyot-talantov.ru/problems/x",
    title: "Problem",
    status,
    ...extra,
  });
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

/** Assert the loading spinner is gone — i.e. we reached a terminal state. */
async function expectNoSpinner(): Promise<void> {
  await waitFor(() => {
    expect(screen.queryByText("Проверяем вашу ссылку…")).not.toBeInTheDocument();
  });
}

describe("VerifyEmailPage", () => {
  it("200 → renders the verified success screen", async () => {
    globalThis.fetch = vi.fn(async () => jsonResponse(200, VERIFIED_USER)) as typeof fetch;

    renderPage("/verify-email?token=abc");

    expect(await screen.findByText("Email подтверждён")).toBeInTheDocument();
    await expectNoSpinner();
    expect(screen.getByRole("link", { name: "Перейти ко входу" })).toBeInTheDocument();
  });

  it("409 → renders the already-verified screen (success-equivalent), not a spinner", async () => {
    globalThis.fetch = vi.fn(async () => problem(409, { code: "IDN-002" })) as typeof fetch;

    renderPage("/verify-email?token=abc");

    expect(await screen.findByText("Email уже подтверждён")).toBeInTheDocument();
    await expectNoSpinner();
    expect(screen.getByRole("link", { name: "Перейти ко входу" })).toBeInTheDocument();
  });

  it("410 → renders the expired screen with a resend action", async () => {
    globalThis.fetch = vi.fn(async () =>
      problem(410, { code: "email-verification-expired" }),
    ) as typeof fetch;

    renderPage("/verify-email?token=abc");

    expect(await screen.findByText("Срок действия ссылки истёк")).toBeInTheDocument();
    await expectNoSpinner();
    expect(screen.getByRole("link", { name: "Отправить письмо повторно" })).toBeInTheDocument();
  });

  it("422 → renders the invalid-token error screen", async () => {
    globalThis.fetch = vi.fn(async () => problem(422)) as typeof fetch;

    renderPage("/verify-email?token=abc");

    expect(await screen.findByText("Не удалось подтвердить email")).toBeInTheDocument();
    await expectNoSpinner();
  });

  it("network failure → renders the connectivity error with a retry action", async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }) as typeof fetch;

    renderPage("/verify-email?token=abc");

    expect(await screen.findByText("Нет соединения")).toBeInTheDocument();
    await expectNoSpinner();
    expect(screen.getByRole("link", { name: "Повторить попытку" })).toBeInTheDocument();
  });

  it("5xx → renders the server error with a retry action", async () => {
    globalThis.fetch = vi.fn(async () => problem(500)) as typeof fetch;

    renderPage("/verify-email?token=abc");

    expect(await screen.findByText("Ошибка сервера")).toBeInTheDocument();
    await expectNoSpinner();
    expect(screen.getByRole("link", { name: "Повторить попытку" })).toBeInTheDocument();
  });

  it("missing token → renders the invalid-link screen without calling the API", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderPage("/verify-email");

    expect(await screen.findByText("Ссылка недействительна")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("StrictMode double-mount: first 200 then 409 still ends verified (never stuck loading)", async () => {
    // Reproduces the original defect: the confirmation is POSTed twice; the
    // first verifies (200), the second is rejected 409. The page must settle on
    // a success-equivalent terminal screen, never an infinite spinner.
    let call = 0;
    globalThis.fetch = vi.fn(async () => {
      call += 1;
      return call === 1 ? jsonResponse(200, VERIFIED_USER) : problem(409, { code: "IDN-002" });
    }) as typeof fetch;

    renderPage("/verify-email?token=abc", { strict: true });

    // Either "Email подтверждён" (200 won) or "Email уже подтверждён" (409 won)
    // is an acceptable terminal success state; both clear the spinner.
    await waitFor(() => {
      expect(
        screen.queryByText("Email подтверждён") ?? screen.queryByText("Email уже подтверждён"),
      ).toBeInTheDocument();
    });
    await expectNoSpinner();
  });
});
