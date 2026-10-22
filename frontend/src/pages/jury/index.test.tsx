import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type JurySeat,
  type JuryTask,
  useJurySeats,
  useJuryTasks,
  useSubmitScorecard,
} from "@/features/judging";

import { JuryScoringPage } from "./index";

vi.mock("@/features/judging", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/judging")>()),
  useJurySeats: vi.fn(),
  useJuryTasks: vi.fn(),
  useSubmitScorecard: vi.fn(),
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

function seat(overrides: Partial<JurySeat> = {}): JurySeat {
  return {
    competitionId: COMPETITION,
    title: "Весна талантов",
    onlineJudging: true,
    isChair: false,
    categoryNames: [],
    startsOn: null,
    endsOn: null,
    venue: null,
    pendingCount: 1,
    hasOpenAct: true,
    ...overrides,
  };
}

function show(
  tasks: JuryTask[],
  state: { isLoading?: boolean; isError?: boolean; seats?: JurySeat[] } = {},
) {
  vi.mocked(useJurySeats).mockReturnValue({
    data: state.seats ?? [seat()],
    isLoading: false,
  } as ReturnType<typeof useJurySeats>);

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

/** The judge's own entry point: `/jury` with no festival in the address. */
function showWithoutRoute(seats: JurySeat[], tasks: JuryTask[] = []) {
  vi.mocked(useJurySeats).mockReturnValue({
    data: seats,
    isLoading: false,
  } as ReturnType<typeof useJurySeats>);
  vi.mocked(useJuryTasks).mockReturnValue({
    data: tasks,
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useJuryTasks>);
  vi.mocked(useSubmitScorecard).mockReturnValue({
    mutateAsync: submit,
    isPending: false,
  } as unknown as ReturnType<typeof useSubmitScorecard>);

  render(
    <MemoryRouter initialEntries={["/jury"]}>
      <Routes>
        <Route path="/jury" element={<JuryScoringPage />} />
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

  it("opens the only festival a judge sits on, without making them pick it", () => {
    // The regression this screen shipped with: the picker was fed the organizer's
    // festival list, which answers a jury member with a 403, so it was always empty
    // and there was nothing to score.
    showWithoutRoute([seat()], [task()]);

    expect(screen.queryByLabelText("Фестиваль")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /7.*Журавли/ })).toBeInTheDocument();
  });

  it("offers a choice to a judge who sits on more than one", () => {
    showWithoutRoute([seat(), seat({ competitionId: "c-2", title: "Осенний бал" })]);

    expect(screen.getByLabelText("Фестиваль")).toBeInTheDocument();
  });

  it("says where an invitation comes from when the account holds no seat at all", () => {
    showWithoutRoute([]);

    expect(screen.getByText("Вас пока не пригласили в жюри")).toBeInTheDocument();
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
