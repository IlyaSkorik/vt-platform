/**
 * Замок редактирования — там же, где остальные выключатели жанра.
 *
 * Три свойства, ради которых тест: закрытие спрашивает подтверждение, открытие не
 * спрашивает ничего (вернуть людям доступ должно быть легче, чем отнять), и обе
 * команды уходят с id жанра — переезд с фестиваля на жанр и был всей задачей.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useDisableNominationWaitlistMutation,
  useEnableNominationWaitlistMutation,
  useResumeNominationRegistrationMutation,
  useScheduleNominationRegistrationMutation,
  useSetSubmissionEditingLockMutation,
  useStopNominationRegistrationMutation,
} from "@/features/competitions";
import type { _Category } from "@/shared/api/generated/model-competitions";

import { NominationRegistration } from "./nomination-registration";

vi.mock("@/features/competitions", () => ({
  useScheduleNominationRegistrationMutation: vi.fn(),
  useStopNominationRegistrationMutation: vi.fn(),
  useResumeNominationRegistrationMutation: vi.fn(),
  useEnableNominationWaitlistMutation: vi.fn(),
  useDisableNominationWaitlistMutation: vi.fn(),
  useSetSubmissionEditingLockMutation: vi.fn(),
}));

const COMPETITION = "01900000-0000-7000-8000-0000000000ee";
const CATEGORY = "01900000-0000-7000-8000-0000000000dd";

const lockEditing = vi.fn();

function aCategory(overrides: Partial<_Category> = {}): _Category {
  return {
    id: CATEGORY,
    name: "Вокал",
    description: null,
    sortOrder: 0,
    registrationOpensAt: null,
    registrationClosesAt: null,
    registrationStopped: false,
    waitlistEnabled: false,
    heldAt: null,
    editingLockedAt: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  lockEditing.mockResolvedValue(undefined);
  const idle = { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false };
  vi.mocked(useScheduleNominationRegistrationMutation).mockReturnValue(
    idle as unknown as ReturnType<typeof useScheduleNominationRegistrationMutation>,
  );
  vi.mocked(useStopNominationRegistrationMutation).mockReturnValue(
    idle as unknown as ReturnType<typeof useStopNominationRegistrationMutation>,
  );
  vi.mocked(useResumeNominationRegistrationMutation).mockReturnValue(
    idle as unknown as ReturnType<typeof useResumeNominationRegistrationMutation>,
  );
  vi.mocked(useEnableNominationWaitlistMutation).mockReturnValue(
    idle as unknown as ReturnType<typeof useEnableNominationWaitlistMutation>,
  );
  vi.mocked(useDisableNominationWaitlistMutation).mockReturnValue(
    idle as unknown as ReturnType<typeof useDisableNominationWaitlistMutation>,
  );
  vi.mocked(useSetSubmissionEditingLockMutation).mockReturnValue({
    mutateAsync: lockEditing,
    isPending: false,
  } as unknown as ReturnType<typeof useSetSubmissionEditingLockMutation>);
});

describe("NominationRegistration — замок редактирования", () => {
  it("спрашивает, прежде чем заморозить жанр, и уходит с его id", async () => {
    render(<NominationRegistration competitionId={COMPETITION} category={aCategory()} />);

    await userEvent.click(screen.getByRole("button", { name: /Закрыть редактирование/ }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent(/«Вокал»/);
    expect(dialog).toHaveTextContent(/Другие жанры продолжают работать/);
    expect(lockEditing).not.toHaveBeenCalled();

    await userEvent.click(within(dialog).getByRole("button", { name: /^Закрыть редактирование$/ }));

    await waitFor(() =>
      expect(lockEditing).toHaveBeenCalledWith({
        competitionId: COMPETITION,
        categoryId: CATEGORY,
        locked: true,
      }),
    );
  });

  it("открывает обратно без второго вопроса", async () => {
    render(
      <NominationRegistration
        competitionId={COMPETITION}
        category={aCategory({ editingLockedAt: "2026-05-01T15:00:00Z" })}
      />,
    );

    expect(screen.getByText(/Правки закрыты/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Открыть редактирование/ }));

    await waitFor(() =>
      expect(lockEditing).toHaveBeenCalledWith({
        competitionId: COMPETITION,
        categoryId: CATEGORY,
        locked: false,
      }),
    );
  });

  it("ничего не предлагает на завершённом фестивале", () => {
    render(<NominationRegistration competitionId={COMPETITION} category={aCategory()} disabled />);

    expect(screen.getByRole("button", { name: /Закрыть редактирование/ })).toBeDisabled();
  });
});
