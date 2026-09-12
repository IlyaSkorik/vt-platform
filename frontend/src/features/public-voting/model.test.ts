import { describe, expect, it } from "vitest";

import type { PublicBallot, PublicNominee } from "./api";
import { barWidth, canPick, canVote, closedLabel, hasVoted, ranked, votesLeftLabel } from "./model";

function nominee(overrides: Partial<PublicNominee> = {}): PublicNominee {
  return {
    id: "n-1",
    position: 1,
    title: "Ансамбль «Ритм»",
    subtitle: "",
    city: "",
    photo: null,
    number: null,
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
    nominees: [nominee()],
    totalVotes: null,
    closesAt: null,
    closedReason: null,
    ...overrides,
  };
}

describe("whether the page does anything", () => {
  it("an open ballot with a vote left is votable", () => {
    expect(canVote(ballot())).toBe(true);
  });

  it("a closed ballot is not", () => {
    expect(canVote(ballot({ open: false }))).toBe(false);
  });

  it("a spent allowance is not", () => {
    expect(canVote(ballot({ votesLeft: 0 }))).toBe(false);
  });

  it("a page still loading is not", () => {
    expect(canVote(undefined)).toBe(false);
  });

  it("a nominee already backed stays inert", () => {
    const chosen = nominee({ chosen: true });

    expect(canPick(ballot({ nominees: [chosen] }), chosen)).toBe(false);
  });

  it("an untouched nominee on an open ballot is tappable", () => {
    expect(canPick(ballot(), nominee())).toBe(true);
  });
});

describe("what the page says", () => {
  it("says nothing about the allowance on a one-vote ballot", () => {
    expect(votesLeftLabel(ballot())).toBeNull();
  });

  it("counts down on a ballot allowing several", () => {
    expect(votesLeftLabel(ballot({ votesPerVoter: 3, votesLeft: 2 }))).toBe(
      "Осталось голосов: 2 из 3",
    );
  });

  it("says so once the allowance is spent", () => {
    expect(votesLeftLabel(ballot({ votesPerVoter: 3, votesLeft: 0 }))).toBe(
      "Вы использовали все свои голоса",
    );
  });

  it("prefers the server's own reason for being closed", () => {
    expect(closedLabel(ballot({ open: false, closedReason: "Голосование ещё не началось." }))).toBe(
      "Голосование ещё не началось.",
    );
  });

  it("falls back to something sensible when the server said nothing", () => {
    expect(closedLabel(ballot({ open: false, status: "CLOSED" }))).toBe("Голосование завершено.");
  });

  it("says nothing while the vote is open", () => {
    expect(closedLabel(ballot())).toBeNull();
  });

  it("knows whether this reader has spent anything", () => {
    expect(hasVoted(ballot())).toBe(false);
    expect(hasVoted(ballot({ nominees: [nominee({ chosen: true })] }))).toBe(true);
  });
});

describe("the board", () => {
  it("puts the leader first", () => {
    const rows = [
      nominee({ id: "a", position: 1, votes: 3 }),
      nominee({ id: "b", position: 2, votes: 9 }),
    ];

    expect(ranked(rows).map((row) => row.id)).toEqual(["b", "a"]);
  });

  it("breaks a tie by the ballot's own order, so it does not reshuffle on every poll", () => {
    const rows = [
      nominee({ id: "b", position: 2, votes: 0 }),
      nominee({ id: "a", position: 1, votes: 0 }),
    ];

    expect(ranked(rows).map((row) => row.id)).toEqual(["a", "b"]);
  });

  it("does not mutate what it was given", () => {
    const rows = [
      nominee({ id: "a", position: 1, votes: 1 }),
      nominee({ id: "b", position: 2, votes: 5 }),
    ];

    ranked(rows);

    expect(rows.map((row) => row.id)).toEqual(["a", "b"]);
  });

  it("scales the bars to the leader, so a wide field stays readable", () => {
    const rows = [nominee({ id: "a", votes: 10 }), nominee({ id: "b", votes: 5 })];

    expect(barWidth(rows[0] as PublicNominee, rows)).toBe(100);
    expect(barWidth(rows[1] as PublicNominee, rows)).toBe(50);
  });

  it("draws nothing before anybody has voted", () => {
    const rows = [nominee({ id: "a", votes: 0 }), nominee({ id: "b", votes: 0 })];

    expect(barWidth(rows[0] as PublicNominee, rows)).toBe(0);
  });

  it("treats a hidden count as nothing to draw", () => {
    const rows = [nominee({ id: "a", votes: null })];

    expect(barWidth(rows[0] as PublicNominee, rows)).toBe(0);
  });
});
