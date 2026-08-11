import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ROUTES } from "@/shared/config";
import { RegisterForm } from "./register-form";

function renderForm(onSuccess = vi.fn()): { onSuccess: ReturnType<typeof vi.fn> } {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  render(<RegisterForm onSuccess={onSuccess} />, { wrapper });
  return { onSuccess };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText("Имя"), "Ирина");
  await user.type(screen.getByLabelText("Фамилия"), "Смирнова");
  await user.type(screen.getByLabelText("Email"), "irina@example.com");
  await user.type(screen.getByLabelText("Пароль"), "SuperSecret123");
  await user.type(screen.getByLabelText("Подтверждение пароля"), "SuperSecret123");
  await tickRequiredConsents(user);
}

/**
 * Accept the agreement — the one box the account cannot be created without — and leave
 * the optional one alone, which is also the assertion that it *is* optional: every test
 * that submits successfully does so without agreeing to marketing.
 */
async function tickRequiredConsents(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  const boxes = screen.getAllByRole("checkbox");
  await user.click(boxes[0] as HTMLElement);
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("RegisterForm", () => {
  it("blocks submit and shows the error until the agreement is accepted", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Имя"), "Ирина");
    await user.type(screen.getByLabelText("Фамилия"), "Смирнова");
    await user.type(screen.getByLabelText("Email"), "irina@example.com");
    await user.type(screen.getByLabelText("Пароль"), "SuperSecret123");
    await user.type(screen.getByLabelText("Подтверждение пароля"), "SuperSecret123");
    await user.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    expect(
      await screen.findByText(/Необходимо принять Пользовательское соглашение/),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("asks for no consent the account cannot be created without", async () => {
    // The account's data rests on the agreement, not on consent (LEGAL-001 §4.4). A second
    // required box here would mean a consent that has to be given for the service to work —
    // exactly what §13.1 says a consent cannot be.
    renderForm();

    const boxes = screen.getAllByRole("checkbox");
    expect(boxes).toHaveLength(2);
    expect(screen.getByText(/Я принимаю Пользовательское соглашение/)).toBeInTheDocument();
    expect(screen.getByText(/информационные рассылки/)).toBeInTheDocument();
  });

  it("links the agreement and the policy from the form itself", async () => {
    // LEGAL-003 §3.3: the documents have to be readable before the box is ticked, from the
    // form and not only from the footer.
    renderForm();

    expect(screen.getByRole("link", { name: "Пользовательское соглашение" })).toHaveAttribute(
      "href",
      ROUTES.termsOfService,
    );
    // Both boxes link the policy — the agreement's own list and the newsletter's default —
    // so every one of them has to resolve, not just the first.
    const policyLinks = screen.getAllByRole("link", {
      name: "Политика в отношении обработки персональных данных",
    });
    expect(policyLinks.length).toBeGreaterThan(0);
    for (const link of policyLinks) {
      expect(link).toHaveAttribute("href", ROUTES.privacyPolicy);
    }
  });

  it("flags mismatched password confirmation", async () => {
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Имя"), "Ирина");
    await user.type(screen.getByLabelText("Фамилия"), "Смирнова");
    await user.type(screen.getByLabelText("Email"), "irina@example.com");
    await user.type(screen.getByLabelText("Пароль"), "SuperSecret123");
    await user.type(screen.getByLabelText("Подтверждение пароля"), "Mismatch12345");
    await tickRequiredConsents(user);
    await user.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    expect(await screen.findByText("Пароли не совпадают")).toBeInTheDocument();
  });

  it("calls onSuccess with the email on a successful registration", async () => {
    globalThis.fetch = vi.fn(async () =>
      jsonResponse(201, {
        data: {
          id: "1",
          type: "user",
          email: "irina@example.com",
          displayName: "Ирина Смирнова",
          status: "registered",
          emailVerified: false,
        },
      }),
    ) as unknown as typeof fetch;
    const user = userEvent.setup();
    const { onSuccess } = renderForm();

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith("irina@example.com"));
  });

  it("maps a server field error onto the offending field", async () => {
    globalThis.fetch = vi.fn(async () =>
      jsonResponse(422, {
        type: "https://api.vzlyot-talantov.ru/problems/validation-error",
        title: "Validation failed",
        status: 422,
        errors: [
          { pointer: "/password", code: "weak-password", detail: "Пароль найден в утечке." },
        ],
      }),
    ) as unknown as typeof fetch;
    const user = userEvent.setup();
    renderForm();

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    expect(await screen.findByText("Пароль найден в утечке.")).toBeInTheDocument();
  });
});
