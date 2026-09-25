import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSetPayer } from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";

import { PayerCard } from "./payer-card";

vi.mock("@/entities/application", () => ({ useSetPayer: vi.fn() }));

const APPLICATION = "01900000-0000-7000-8000-0000000000aa";

const save = vi.fn();

function aRegistration(collectPayerDetails: boolean): Registration {
  return { collectPayerDetails } as Registration;
}

function anApplication(payer: ApplicationResource["payer"] = null): ApplicationResource {
  return { payer } as ApplicationResource;
}

beforeEach(() => {
  save.mockReset();
  vi.mocked(useSetPayer).mockReturnValue({
    mutate: save,
    isPending: false,
  } as unknown as ReturnType<typeof useSetPayer>);
});

function renderFor({
  collect = true,
  payer = null,
}: {
  collect?: boolean;
  payer?: ApplicationResource["payer"];
} = {}) {
  return render(
    <PayerCard
      applicationId={APPLICATION}
      application={anApplication(payer)}
      registration={aRegistration(collect)}
    />,
  );
}

describe("PayerCard", () => {
  it("is absent where the festival collects no payer", () => {
    // The backend only makes the name a condition of submitting when the festival asks
    // for it, so a festival that issues no documents must not show the block at all.
    const { container } = renderFor({ collect: false });

    expect(container).toBeEmptyDOMElement();
  });

  it("says the name is required while it is incomplete", () => {
    renderFor();

    expect(screen.getByText(/Без ФИО заказчика заявку не примут/)).toBeInTheDocument();
  });

  it("autosaves the name once it is one the backend would accept", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderFor();

    await user.type(screen.getByLabelText(/Фамилия/), "Иванова");
    await user.type(screen.getByLabelText(/Имя/), "Анна");
    await vi.advanceTimersByTimeAsync(800);

    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        { lastName: "Иванова", firstName: "Анна", middleName: null },
        expect.anything(),
      ),
    );
    vi.useRealTimers();
  });

  it("does not save a surname on its own", async () => {
    // A name without a given name is not a name the value object accepts, and writing
    // on every keystroke would reject the whole way from "И" to "Иванова".
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderFor();

    await user.type(screen.getByLabelText(/Фамилия/), "Иванова");
    await vi.advanceTimersByTimeAsync(1500);

    expect(save).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("prefills the payer already on the order and saves nothing on open", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderFor({
      payer: {
        lastName: "Иванова",
        firstName: "Анна",
        middleName: "Сергеевна",
        fullName: "Иванова Анна Сергеевна",
      },
    });

    expect(screen.getByLabelText(/Фамилия/)).toHaveValue("Иванова");
    expect(screen.getByLabelText(/Отчество/)).toHaveValue("Сергеевна");
    await vi.advanceTimersByTimeAsync(1500);
    expect(save).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("sends the patronymic when one is typed", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderFor();

    await user.type(screen.getByLabelText(/Фамилия/), "Иванова");
    await user.type(screen.getByLabelText(/Имя/), "Анна");
    await user.type(screen.getByLabelText(/Отчество/), "  Сергеевна  ");
    await vi.advanceTimersByTimeAsync(800);

    await waitFor(() =>
      expect(save).toHaveBeenLastCalledWith(
        { lastName: "Иванова", firstName: "Анна", middleName: "Сергеевна" },
        expect.anything(),
      ),
    );
    vi.useRealTimers();
  });
});

describe("PayerCard — the echo of its own save", () => {
  it("keeps what is being typed when the saved order comes back", async () => {
    // Saving the name invalidates the order, and the refetched order arrives while the
    // applicant is already typing the patronymic. Adopting it wiped that field —
    // the complaint that these boxes erase themselves.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { rerender } = render(
      <PayerCard
        applicationId={APPLICATION}
        application={anApplication(null)}
        registration={aRegistration(true)}
      />,
    );

    await user.type(screen.getByLabelText(/Фамилия/), "Иванова");
    await user.type(screen.getByLabelText(/Имя/), "Анна");
    await vi.advanceTimersByTimeAsync(800);
    await user.type(screen.getByLabelText(/Отчество/), "Сергеевна");

    rerender(
      <PayerCard
        applicationId={APPLICATION}
        application={anApplication({
          lastName: "Иванова",
          firstName: "Анна",
          middleName: null,
          fullName: "Иванова Анна",
        })}
        registration={aRegistration(true)}
      />,
    );

    expect(screen.getByLabelText(/Отчество/)).toHaveValue("Сергеевна");
    await vi.advanceTimersByTimeAsync(800);
    await waitFor(() =>
      expect(save).toHaveBeenLastCalledWith(
        { lastName: "Иванова", firstName: "Анна", middleName: "Сергеевна" },
        expect.anything(),
      ),
    );
    vi.useRealTimers();
  });

  it("adopts a name changed elsewhere while this card sits untouched", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { rerender } = render(
      <PayerCard
        applicationId={APPLICATION}
        application={anApplication(null)}
        registration={aRegistration(true)}
      />,
    );

    rerender(
      <PayerCard
        applicationId={APPLICATION}
        application={anApplication({
          lastName: "Петрова",
          firstName: "Ольга",
          middleName: "Ивановна",
          fullName: "Петрова Ольга Ивановна",
        })}
        registration={aRegistration(true)}
      />,
    );

    expect(screen.getByLabelText(/Фамилия/)).toHaveValue("Петрова");
    expect(screen.getByLabelText(/Отчество/)).toHaveValue("Ивановна");
    await vi.advanceTimersByTimeAsync(1500);
    // Nothing of its own to save: the value shown is the value stored.
    expect(save).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("sends a name still waiting out its debounce when the card goes away", async () => {
    // Leaving the page within the debounce dropped the write with the timer, and the
    // name was never stored at all.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { unmount } = render(
      <PayerCard
        applicationId={APPLICATION}
        application={anApplication(null)}
        registration={aRegistration(true)}
      />,
    );

    await user.type(screen.getByLabelText(/Фамилия/), "Иванова");
    await user.type(screen.getByLabelText(/Имя/), "Анна");
    expect(save).not.toHaveBeenCalled();

    unmount();

    expect(save).toHaveBeenCalledWith(
      { lastName: "Иванова", firstName: "Анна", middleName: null },
      expect.anything(),
    );
    vi.useRealTimers();
  });
});
