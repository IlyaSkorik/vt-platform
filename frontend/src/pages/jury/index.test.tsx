import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type JuryTask, useJuryTasks, useSubmitScorecard } from "@/features/judging";

import { JuryScoringPage } from "./index";

vi.mock("@/features/judging", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/judging")>()),
  useJuryTasks: vi.fn(),
  useSubmitScorecard: vi.fn(),
}));

vi.mock("@/features/competitions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/competitions")>()),
  useCompetitionsList: vi.fn(() => ({ data: [] })),
}));

/**
 * A judge's tablet.
 *
 * The two properties that matter most are asserted here: that a closed act cannot be
 * marked, and that no participant's name appears. The second is ADR-0013 and is kept at
 * the server's boundary — this test asserts the page does not reintroduce it by
 * rendering something it was never given.
 */

const COMPETITION = "c-1";

function task(overrides: Partial<JuryTask> = {}): JuryTask {
  return {
    submissionId: "s-1",
    number: 7,
    title: "Журавли",
    categoryId: "vocals",
    categoryName: "Вокал",
    disciplineName: null,
    ageCategoryName: "10–12 лет",
    participationFormatName: null,
    organization: "ДШИ №3",
    status: "OPEN",
    criteria: [
      {
        id: "k1",
        name: "Техника",
        maxScore: "10.00",
        weight: "1.00",
        sortOrder: 0,
        description: null,
      },
    ],
    myScores: [],
    myComment: null,
    myTotal: null,
    submittedAt: null,
    canScore: true,
    maxTotal: "10.00",
    ...overrides,
  };
}

const submit = vi.fn();

function show(tasks: JuryTask[], state: { isLoading?: boolean; isError?: boolean } = {}) {
  vi.mocked(useJuryTasks).mockReturnValue({
    data: tasks,
    isLoading: state.isLoading ?? false,
    isError: state.isError ?? false,
  } as ReturnType<typeof useJuryTasks>);

  vi.mocked(useSubmitScorecard).mockReturnValue({
    mutateAsync: submit,
    isPending: false,
  } as unknown as ReturnType<typeof useSubmitScorecard>);

  render(
    <MemoryRouter initialEntries={[`/jury/${COMPETITION}`]}>
      <Routes>
        <Route path="/jury/:competitionId" element={<JuryScoringPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("JuryScoringPage", () => {
  beforeEach(() => {
    submit.mockReset();
    submit.mockResolvedValue(task({ myTotal: "9.00", submittedAt: "2026-05-16T11:00:00Z" }));
  });

  it("shows the act the host has opened, under the number it was announced with", () => {
    show([task()]);

    // Asked for as one control rather than as a bare "7": the sheet below it is a row
    // of numbered buttons, and the number a judge needs is the act's.
    expect(screen.getByRole("button", { name: /7.*Журавли/ })).toBeInTheDocument();
  });

  it("shows the act and where it competes, never a participant", () => {
    show([task()]);

    expect(screen.getByText(/Вокал/)).toBeInTheDocument();
    expect(screen.getByText(/ДШИ №3/)).toBeInTheDocument();
    expect(screen.queryByText(/Иванова/)).not.toBeInTheDocument();
  });

  it("sends the sheet with the mark the judge pressed", async () => {
    const user = userEvent.setup();
    show([task()]);

    await user.click(screen.getByRole("button", { name: "Техника: 9" }));
    await user.click(screen.getByRole("button", { name: "Отправить оценку" }));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        competitionId: COMPETITION,
        submissionId: "s-1",
        scores: { k1: "9" },
      }),
    );
  });

  it("will not let a closed act be marked", async () => {
    const user = userEvent.setup();
    show([task({ status: "CLOSED", canScore: false })]);

    await user.click(screen.getByRole("button", { name: /Журавли/ }));

    expect(screen.getByRole("button", { name: "Отправить оценку" })).toBeDisabled();
    expect(
      screen.getByText("Ведущий закрыл это выступление — оценка зафиксирована."),
    ).toBeInTheDocument();
  });

  it("offers to change a sheet that was already sent", () => {
    show([
      task({
        submittedAt: "2026-05-16T11:00:00Z",
        myTotal: "9.00",
        myScores: [{ criterionId: "k1", score: "9.00" }],
      }),
    ]);

    expect(screen.getByRole("button", { name: "Изменить оценку" })).toBeInTheDocument();
  });

  it("says so when nothing is open, and still lists the acts", () => {
    // The judge may go back to a number they missed, which is the whole reason the
    // list stays on screen when the host is between acts.
    show([task({ status: "PENDING", canScore: false })]);

    expect(screen.getByText("Ждём ведущего")).toBeInTheDocument();
    expect(screen.getByText("Журавли")).toBeInTheDocument();
  });

  it("explains an account that holds no seat here", () => {
    show([], { isError: true });

    expect(screen.getByText("Нет доступа к оценке")).toBeInTheDocument();
  });

  it("says when a genre has no criteria rather than showing an empty sheet", () => {
    show([task({ criteria: [] })]);

    expect(screen.getByText("Для этого жанра нет критериев")).toBeInTheDocument();
  });
});
