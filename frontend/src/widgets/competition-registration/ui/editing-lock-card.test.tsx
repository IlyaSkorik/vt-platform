/**
 * Кнопка, после которой заявитель не меняет ничего, включая файлы.
 *
 * Два свойства, ради которых тест: закрытие спрашивает подтверждение (радиус —
 * все заявители фестиваля сразу), а открытие не спрашивает ничего — вернуть
 * людям доступ должно быть легче, чем отнять.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSetSubmissionEditingLockMutation } from "@/features/competitions";

import { EditingLockCard } from "./editing-lock-card";

vi.mock("@/features/competitions", () => ({
  useSetSubmissionEditingLockMutation: vi.fn(),
}));

const COMPETITION = "01900000-0000-7000-8000-0000000000ee";
const mutate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useSetSubmissionEditingLockMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof useSetSubmissionEditingLockMutation>);
});

describe("EditingLockCard", () => {
  it("asks before freezing the whole festival", async () => {
    render(<EditingLockCard competitionId={COMPETITION} editingLockedAt={null} />);

    await userEvent.click(screen.getByRole("button", { name: /Закрыть редактирование полностью/ }));

    expect(screen.getByRole("dialog")).toHaveTextContent(/включая тех, у кого вы просили/);
    expect(mutate).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /^Закрыть редактирование$/ }));

    await waitFor(() =>
      expect(mutate).toHaveBeenCalledWith(
        { competitionId: COMPETITION, locked: true },
        expect.anything(),
      ),
    );
  });

  it("lifts the freeze without a second question", async () => {
    render(<EditingLockCard competitionId={COMPETITION} editingLockedAt="2026-05-01T15:00:00Z" />);

    expect(screen.getByText("Закрыто")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Открыть редактирование/ }));

    expect(mutate).toHaveBeenCalledWith(
      { competitionId: COMPETITION, locked: false },
      expect.anything(),
    );
  });

  it("offers nothing on a finished festival", () => {
    render(<EditingLockCard competitionId={COMPETITION} editingLockedAt={null} disabled />);

    expect(screen.getByRole("button", { name: /Закрыть редактирование полностью/ })).toBeDisabled();
  });
});
