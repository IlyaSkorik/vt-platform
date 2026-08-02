import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/shared/api";

import { useChangePassword } from "../api/hooks";
import { PasswordCard } from "./password-card";

vi.mock("../api/hooks", () => ({ useChangePassword: vi.fn() }));

const change = vi.fn();
const STRONG = "N3wStrongPass!";

beforeEach(() => {
  vi.clearAllMocks();
  change.mockResolvedValue({});
  vi.mocked(useChangePassword).mockReturnValue({
    mutateAsync: change,
    isPending: false,
  } as unknown as ReturnType<typeof useChangePassword>);
});

async function fill(current: string, next: string, confirm = next) {
  await userEvent.type(screen.getByLabelText("Текущий пароль"), current);
  await userEvent.type(screen.getByLabelText("Новый пароль"), next);
  await userEvent.type(screen.getByLabelText("Повторите новый пароль"), confirm);
  await userEvent.click(screen.getByRole("button", { name: "Сохранить пароль" }));
}

describe("PasswordCard", () => {
  it("sends the current password along with the new one", async () => {
    render(<PasswordCard />);

    await fill("OldPass!12345", STRONG);

    await waitFor(() =>
      expect(change).toHaveBeenCalledWith({
        currentPassword: "OldPass!12345",
        newPassword: STRONG,
      }),
    );
  });

  it("refuses to send a new password that was typed twice differently", async () => {
    render(<PasswordCard />);

    await fill("OldPass!12345", STRONG, "N3wStrongPass!x");

    expect(await screen.findByText("Пароли не совпадают")).toBeInTheDocument();
    expect(change).not.toHaveBeenCalled();
  });

  it("refuses a new password that is the current one", async () => {
    render(<PasswordCard />);

    await fill(STRONG, STRONG);

    expect(await screen.findByText("Новый пароль совпадает с текущим")).toBeInTheDocument();
    expect(change).not.toHaveBeenCalled();
  });

  it("surfaces the server's refusal instead of a blank failure", async () => {
    change.mockRejectedValue(new ApiError("The current password is incorrect.", { status: 401 }));
    render(<PasswordCard />);

    await fill("WrongPass!123", STRONG);

    expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось изменить пароль");
  });
});
