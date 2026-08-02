import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useChangePhone } from "../api/hooks";
import { PhoneCard } from "./phone-card";

vi.mock("../api/hooks", () => ({ useChangePhone: vi.fn() }));

const change = vi.fn();
const onChanged = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  change.mockResolvedValue({});
  vi.mocked(useChangePhone).mockReturnValue({
    mutateAsync: change,
    isPending: false,
  } as unknown as ReturnType<typeof useChangePhone>);
});

describe("PhoneCard", () => {
  it("invites a first number when the account has none", () => {
    render(<PhoneCard phone={null} onChanged={onChanged} />);

    expect(screen.getByRole("button", { name: "Добавить номер" })).toBeInTheDocument();
  });

  it("accepts the way Russian numbers are actually written", async () => {
    render(<PhoneCard phone={null} onChanged={onChanged} />);

    // Typed as everybody types it; sent in the E.164 the backend's value object wants.
    await userEvent.type(screen.getByLabelText("Номер телефона"), "8 (999) 123-45-67");
    await userEvent.tab();
    await userEvent.click(screen.getByRole("button", { name: "Добавить номер" }));

    await waitFor(() => expect(change).toHaveBeenCalledWith({ phone: "+79991234567" }));
    expect(onChanged).toHaveBeenCalled();
  });

  it("has nothing to save until the number is edited", () => {
    render(<PhoneCard phone="+79991234567" onChanged={onChanged} />);

    expect(screen.getByRole("button", { name: "Сохранить номер" })).toBeDisabled();
  });
});
