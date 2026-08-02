import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useResendVerification } from "@/features/auth";

import { useChangeEmail } from "../api/hooks";
import { EmailCard } from "./email-card";

vi.mock("../api/hooks", () => ({ useChangeEmail: vi.fn() }));
vi.mock("@/features/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/auth")>()),
  useResendVerification: vi.fn(),
}));

const change = vi.fn();
const resend = vi.fn();
const onChanged = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  change.mockResolvedValue({});
  vi.mocked(useChangeEmail).mockReturnValue({
    mutateAsync: change,
    isPending: false,
  } as unknown as ReturnType<typeof useChangeEmail>);
  vi.mocked(useResendVerification).mockReturnValue({
    mutate: resend,
    isPending: false,
  } as unknown as ReturnType<typeof useResendVerification>);
});

function renderCard(verified: boolean) {
  return render(<EmailCard email="holder@example.com" verified={verified} onChanged={onChanged} />);
}

describe("EmailCard", () => {
  it("says the address is confirmed and offers nothing to fix", () => {
    renderCard(true);

    expect(screen.getByText("Подтверждён")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Отправить письмо ещё раз/ }),
    ).not.toBeInTheDocument();
  });

  it("explains the consequence of an unconfirmed address and offers a fresh link", async () => {
    renderCard(false);

    expect(screen.getByText("Не подтверждён")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Отправить письмо ещё раз/ }));

    expect(resend).toHaveBeenCalledWith("holder@example.com", expect.anything());
  });

  it("asks for the password before moving the address", async () => {
    renderCard(true);

    await userEvent.click(screen.getByRole("button", { name: "Изменить" }));
    await userEvent.type(screen.getByLabelText("Новый адрес"), "moved@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить адрес" }));

    // Nothing is sent while the confirmation is missing.
    expect(change).not.toHaveBeenCalled();
    expect(await screen.findByText(/Введите пароль/)).toBeInTheDocument();
  });

  it("sends the change and re-reads the account", async () => {
    renderCard(true);

    await userEvent.click(screen.getByRole("button", { name: "Изменить" }));
    await userEvent.type(screen.getByLabelText("Новый адрес"), "moved@example.com");
    await userEvent.type(screen.getByLabelText("Текущий пароль"), "OldPass!12345");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить адрес" }));

    await waitFor(() =>
      expect(change).toHaveBeenCalledWith({
        email: "moved@example.com",
        currentPassword: "OldPass!12345",
      }),
    );
    expect(onChanged).toHaveBeenCalled();
  });
});
