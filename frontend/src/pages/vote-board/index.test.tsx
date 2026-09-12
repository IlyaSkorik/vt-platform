import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { type PublicBallot, type PublicNominee, usePublicBallot } from "@/features/public-voting";

import { PublicVoteBoardPage } from "./index";

vi.mock("@/features/public-voting", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-voting")>()),
  usePublicBallot: vi.fn(),
}));

function nominee(overrides: Partial<PublicNominee> = {}): PublicNominee {
  return {
    id: "n-1",
    position: 1,
    title: "Ансамбль «Ритм»",
    subtitle: "",
    photo: null,
    number: null,
    votes: 0,
    chosen: false,
    ...overrides,
  };
}

function ballot(overrides: Partial<PublicBallot> = {}): PublicBallot {
  return {
    title: "Приз зрительских симпатий",
    description: "",
    slug: "AbX82Kqm9p",
    status: "OPEN",
    open: true,
    votesPerVoter: 1,
    votesLeft: 1,
    revealTotals: true,
    nominees: [
      nominee({ id: "a", position: 1, title: "Первый", votes: 3 }),
      nominee({ id: "b", position: 2, title: "Второй", votes: 9 }),
    ],
    totalVotes: 12,
    closesAt: null,
    closedReason: null,
    ...overrides,
  };
}

function show(
  data: PublicBallot | undefined,
  state: { isLoading?: boolean; isError?: boolean } = {},
) {
  vi.mocked(usePublicBallot).mockReturnValue({
    data,
    isLoading: state.isLoading ?? false,
    isError: state.isError ?? false,
  } as ReturnType<typeof usePublicBallot>);

  render(
    <MemoryRouter initialEntries={["/vote/AbX82Kqm9p/board"]}>
      <Routes>
        <Route path="/vote/:slug/board" element={<PublicVoteBoardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("the scoreboard", () => {
  it("puts the leader at the top", () => {
    show(ballot());

    const places = screen.getAllByRole("listitem");
    expect(places[0]).toHaveTextContent("Второй");
    expect(places[1]).toHaveTextContent("Первый");
  });

  it("shows the running total", () => {
    show(ballot());

    expect(screen.getByText("Всего голосов: 12")).toBeInTheDocument();
  });

  it("keeps polling while out of sight — nothing brings a projector to the foreground", () => {
    show(ballot());

    expect(vi.mocked(usePublicBallot)).toHaveBeenCalledWith("AbX82Kqm9p", { live: true });
  });

  it("says the count is hidden rather than showing a board of noughts", () => {
    show(ballot({ revealTotals: false, totalVotes: null }));

    expect(screen.getByText("Результаты скрыты до завершения")).toBeInTheDocument();
    expect(screen.queryByText("Первый")).not.toBeInTheDocument();
  });

  it("says when the vote is over", () => {
    show(ballot({ open: false, status: "CLOSED", closedReason: "Голосование завершено." }));

    expect(screen.getByText("Голосование завершено.")).toBeInTheDocument();
  });

  it("a dead link says so", () => {
    show(undefined, { isError: true });

    expect(screen.getByText("Голосование не найдено")).toBeInTheDocument();
  });
});
