import { describe, expect, it } from "vitest";

import {
  formatBand,
  formatScore,
  genresWithoutCriteria,
  type JudgingSetup,
  judgingReadiness,
  scoreToNumber,
} from "./model";

/**
 * The client-side helpers, and only the ones that make a decision.
 *
 * The arithmetic itself is the server's — it is decimal there for a reason — so what is
 * asserted here is presentation and the one readiness check a browser is allowed to
 * make: whether an organizer who switched online judging on has finished setting it up.
 */

function setup(overrides: Partial<JudgingSetup> = {}): JudgingSetup {
  return {
    competitionId: "c1",
    onlineJudging: true,
    awardScale: [{ code: "FIRST", label: "1 место", minScore: "9", maxScore: "10", sortOrder: 0 }],
    criteriaSets: [
      {
        scope: "CATEGORY",
        targetId: "vocals",
        targetName: "Вокал",
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
        maxTotal: "10.00",
      },
    ],
    nominations: [{ categoryId: "vocals", name: "Вокал", disciplines: [] }],
    aggregation: "AVERAGE",
    dropHighest: false,
    dropLowest: false,
    tallyDimensions: ["CATEGORY"],
    boardEnabled: false,
    boardVisibility: "TOTAL_ONLY",
    boardReveal: "AFTER_CLOSE",
    boardShowAward: true,
    boardShowRunningOrder: true,
    boardSlug: null,
    boardPath: null,
    juryCount: 3,
    scaleIsBanded: true,
    updatedAt: null,
    ...overrides,
  };
}

describe("formatScore", () => {
  it("writes a score the way a Russian screen reads it", () => {
    expect(formatScore("9.50")).toBe("9,5");
    expect(formatScore("10.00")).toBe("10");
  });

  it("shows a dash rather than a zero for an unjudged act", () => {
    // A zero is a panel that judged the act and thought little of it; the two must
    // never look the same on a board in a hall.
    expect(formatScore(null)).toBe("—");
    expect(formatScore("0.00")).toBe("0");
  });
});

describe("formatBand", () => {
  it("writes a closed band as a range", () => {
    expect(formatBand({ minScore: "90", maxScore: "100" })).toBe("90–100");
  });

  it("writes an open top and an open bottom in words", () => {
    expect(formatBand({ minScore: "95", maxScore: null })).toBe("от 95");
    expect(formatBand({ minScore: null, maxScore: "59.99" })).toBe("до 59,99");
  });

  it("says a tier with no band has none", () => {
    expect(formatBand({ minScore: null, maxScore: null })).toBe("—");
  });
});

describe("scoreToNumber", () => {
  it("parses a decimal string for drawing", () => {
    expect(scoreToNumber("9.50")).toBe(9.5);
  });

  it("treats anything unreadable as zero rather than NaN", () => {
    expect(scoreToNumber(null)).toBe(0);
    expect(scoreToNumber("—")).toBe(0);
  });
});

describe("genresWithoutCriteria", () => {
  it("finds the genre a jury would have nothing to fill in for", () => {
    const withExtraGenre = setup({
      nominations: [
        { categoryId: "vocals", name: "Вокал", disciplines: [] },
        { categoryId: "dance", name: "Хореография", disciplines: [] },
      ],
    });

    expect(genresWithoutCriteria(withExtraGenre).map((item) => item.name)).toEqual(["Хореография"]);
  });

  it("counts a nomination's own sheet as not covering its genre", () => {
    // A discipline sheet replaces its genre's for that nomination only; the rest of
    // the genre still has nothing.
    const overriddenOnly = setup({
      criteriaSets: [
        {
          scope: "DISCIPLINE",
          targetId: "pop-vocals",
          targetName: "Эстрадный вокал",
          criteria: [],
          maxTotal: "0",
        },
      ],
    });

    expect(genresWithoutCriteria(overriddenOnly)).toHaveLength(1);
  });
});

describe("judgingReadiness", () => {
  it("is ready when the criteria, the bands and the panel are all there", () => {
    expect(judgingReadiness(setup())).toEqual({ ready: true, problems: [] });
  });

  it("names the genres nobody has written criteria for", () => {
    const missing = setup({ criteriaSets: [] });

    expect(judgingReadiness(missing).problems.join(" ")).toContain("Вокал");
  });

  it("warns that an unbanded scale will award nothing", () => {
    // The failure that only shows up after a festival has been judged: every act has a
    // score and not one of them has a result.
    const unbanded = setup({ scaleIsBanded: false });

    expect(judgingReadiness(unbanded).problems.join(" ")).toContain("диапазоны");
  });

  it("warns about an empty jury", () => {
    expect(judgingReadiness(setup({ juryCount: 0 })).problems.join(" ")).toContain("жюри");
  });

  it("sends an organizer with no genres to the taxonomy rather than to the criteria", () => {
    const noGenres = setup({ nominations: [], criteriaSets: [] });

    expect(judgingReadiness(noGenres).problems.join(" ")).toContain("Жанры и номинации");
  });
});
