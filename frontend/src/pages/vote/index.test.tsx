import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type PublicBallot,
  type PublicNominee,
  useCastVote,
  usePublicBallot,
} from "@/features/public-voting";

import { PublicVotePage } from "./index";

vi.mock("@/features/public-voting", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/public-voting")>()),
  usePublicBallot: vi.fn(),
  useCastVote: vi.fn(),
}));

vi.mock("@/shared/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/ui")>();
  return { ...actual, toast: { ...actual.toast, error: vi.fn(), success: vi.fn() } };
});

const cast = vi.fn();

function nominee(overrides: Partial<PublicNominee> = {}): PublicNominee {
  return {
    id: "n-1",
    position: 1,
    title: "Ансамбль «Ритм»",
    subtitle: "«Калинка»",
    city: "Минск",
    photo: null,
    number: 1,
    votes: null,
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
    revealTotals: false,
    nominees: [nominee(), nominee({ id: "n-2", position: 2, number: 2, title: "Хор «Родник»" })],
    totalVotes: null,
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
    <MemoryRouter initialEntries={["/vote/AbX82Kqm9p"]}>
      <Routes>
        <Route path="/vote/:slug" element={<PublicVotePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  cast.mockReset();
  vi.mocked(useCastVote).mockReturnValue({
    mutate: cast,
    isPending: false,
  } as unknown as ReturnType<typeof useCastVote>);
});

describe("the voting page", () => {
  it("shows the question and every option", () => {
    show(ballot());

    expect(screen.getByRole("heading", { name: "Приз зрительских симпатий" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Голосовать за «Ансамбль «Ритм»»" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Голосовать за «Хор «Родник»»" }),
    ).toBeInTheDocument();
  });

  it("leads with the number the host just read out", () => {
    show(ballot());

    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("a tap votes, with no confirmation step in between", async () => {
    show(ballot());

    await userEvent.click(screen.getByRole("button", { name: "Голосовать за «Ансамбль «Ритм»»" }));

    expect(cast).toHaveBeenCalledWith(["n-1"], expect.anything());
  });

  it("says thank you once the allowance is spent", () => {
    show(ballot({ votesLeft: 0, nominees: [nominee({ chosen: true })] }));

    expect(screen.getByText("Спасибо! Ваш голос учтён.")).toBeInTheDocument();
  });

  it("a nominee already backed is inert", async () => {
    show(ballot({ votesLeft: 0, nominees: [nominee({ chosen: true })] }));

    await userEvent.click(screen.getByRole("button", { name: "Голосовать за «Ансамбль «Ритм»»" }));

    expect(cast).not.toHaveBeenCalled();
  });

  it("a closed ballot says why in words for a person", () => {
    show(ballot({ open: false, status: "CLOSED", closedReason: "Голосование завершено." }));

    expect(screen.getByText("Голосование завершено.")).toBeInTheDocument();
  });

  it("a closed ballot takes no taps", async () => {
    show(ballot({ open: false, closedReason: "Голосование завершено." }));

    await userEvent.click(screen.getByRole("button", { name: "Голосовать за «Ансамбль «Ритм»»" }));

    expect(cast).not.toHaveBeenCalled();
  });

  it("hides the count when the ballot does", () => {
    show(ballot());

    expect(screen.queryByText("Всего голосов: 0")).not.toBeInTheDocument();
  });

  it("shows the count when the ballot allows it", () => {
    show(
      ballot({
        revealTotals: true,
        totalVotes: 7,
        nominees: [nominee({ votes: 5 }), nominee({ id: "n-2", position: 2, votes: 2 })],
      }),
    );

    expect(screen.getByText("Всего голосов: 7")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("counts down on a ballot allowing several picks", () => {
    show(ballot({ votesPerVoter: 3, votesLeft: 2 }));

    expect(screen.getByText("Осталось голосов: 2 из 3")).toBeInTheDocument();
  });

  it("a dead link says so rather than showing an empty page", () => {
    show(undefined, { isError: true });

    expect(screen.getByText("Голосование не найдено")).toBeInTheDocument();
  });
});
