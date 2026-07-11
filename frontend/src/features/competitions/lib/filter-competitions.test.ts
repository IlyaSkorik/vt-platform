import { describe, expect, it } from "vitest";
import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { filterAndSortCompetitions } from "./filter-competitions";

const sample: CompetitionSummary[] = [
  {
    id: "1",
    title: "Alpha Cup",
    season: "2025/2026",
    status: "DRAFT",
    organizerId: "org-1",
    description: null,
    createdAt: "2026-01-01T00:00:00.000Z",
    updatedAt: "2026-01-03T00:00:00.000Z",
    version: 1,
  },
  {
    id: "2",
    title: "Beta Festival",
    season: "2024/2025",
    status: "PUBLISHED",
    organizerId: "org-1",
    description: "Dance",
    createdAt: "2025-01-01T00:00:00.000Z",
    updatedAt: "2026-01-01T00:00:00.000Z",
    version: 1,
  },
];

describe("filterAndSortCompetitions", () => {
  it("filters by search query and status", () => {
    const result = filterAndSortCompetitions(sample, {
      search: "beta",
      status: "PUBLISHED",
      sort: "NEWEST",
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.title).toBe("Beta Festival");
  });

  it("sorts by name", () => {
    const result = filterAndSortCompetitions(sample, {
      search: "",
      status: "ALL",
      sort: "NAME",
    });

    expect(result.map((item) => item.title)).toEqual(["Alpha Cup", "Beta Festival"]);
  });
});
