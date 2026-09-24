import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { type Board, type BoardEntry, useBoard } from "@/features/judging";

import { JudgingBoardPage } from "./index";

vi.mock("@/features/judging", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/judging")>()),
  useBoard: vi.fn(),
}));

/**
 * The screen beside the stage.
 *
 * What is asserted here is what the page renders, not what it *decides* — a board set
 * to totals only has no per-judge marks in the payload at all, because the filtering is
 * the server's. So these tests feed it the payload each configuration actually
 * produces, and check the hall sees the right thing.
 */

function entry(overrides: Partial<BoardEntry> = {}): BoardEntry {
  return {
    number: 7,
    title: "Журавли",
    organization: "ДШИ №3",
    categoryName: "Вокал",
    ageCategoryName: "10–12 лет",
    status: "OPEN",
    score: null,
    maxScore: "10.00",
    awardLabel: null,
    submittedCount: 0,
    expectedJudges: 5,
    judges: [],
    ...overrides,
  };
}

function board(overrides: Partial<Board> = {}): Board {
  return {
    competitionTitle: "Весна талантов",
    visibility: "TOTAL_ONLY",
    reveal: "AFTER_CLOSE",
    showAward: true,
    current: entry(),
    recent: [],
    ...overrides,
  };
}

function show(data: Board | undefined, state: { isLoading?: boolean; isError?: boolean } = {}) {
  vi.mocked(useBoard).mockReturnValue({
    data,
    isLoading: state.isLoading ?? false,
    isError: state.isError ?? false,
  } as ReturnType<typeof useBoard>);

  render(
    <MemoryRouter initialEntries={["/board/AbX82Kqm9p"]}>
      <Routes>
        <Route path="/board/:slug" element={<JudgingBoardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("JudgingBoardPage", () => {
  it("names the festival and the act on stage", () => {
    show(board());

    expect(screen.getByText("Весна талантов")).toBeInTheDocument();
    expect(screen.getByText("Журавли")).toBeInTheDocument();
  });

  it("counts the sheets that are in while the marks are still held back", () => {
    // The `AFTER_CLOSE` case: the hall knows the panel is working without being shown
    // a number that could still change.
    show(board({ current: entry({ submittedCount: 3, expectedJudges: 5 }) }));

    expect(screen.getByText("3 / 5")).toBeInTheDocument();
  });

  it("shows the score and the award once the act is closed", () => {
    show(
      board({
        current: entry({ status: "CLOSED", score: "9.50", awardLabel: "1 место" }),
      }),
    );

    expect(screen.getByText("9,5")).toBeInTheDocument();
    expect(screen.getByText("1 место")).toBeInTheDocument();
  });

  it("names every judge when the organizer asked for per-judge marks", () => {
    show(
      board({
        visibility: "PER_JUDGE",
        reveal: "IMMEDIATE",
        current: entry({
          score: "9.50",
          judges: [
            { name: "Иванова А.", total: "9.00" },
            { name: "Петров Б.", total: "10.00" },
          ],
        }),
      }),
    );

    expect(screen.getByText("Иванова А.")).toBeInTheDocument();
    expect(screen.getByText("Петров Б.")).toBeInTheDocument();
  });

  it("says it is waiting when the host has not opened anything", () => {
    show(board({ current: null }));

    expect(screen.getByText("Ожидание следующего номера")).toBeInTheDocument();
  });

  it("lists the acts already marked under the current one", () => {
    show(
      board({
        recent: [entry({ number: 6, title: "Вальс", status: "CLOSED", score: "8.20" })],
      }),
    );

    expect(screen.getByText("Уже оценены")).toBeInTheDocument();
    expect(screen.getByText("Вальс")).toBeInTheDocument();
  });

  it("explains a link that no longer resolves", () => {
    // Which is what switching the board off does, and the sentence has to say so:
    // somebody is standing at a projector wondering whether they mistyped.
    show(undefined, { isError: true });

    expect(screen.getByText("Табло не найдено")).toBeInTheDocument();
  });
});
