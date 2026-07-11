import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import {
  type CompetitionSortOption,
  type CompetitionStatusFilter,
  matchesStatusFilter,
} from "../model/status";

export interface CompetitionsListFilters {
  search: string;
  status: CompetitionStatusFilter;
  sort: CompetitionSortOption;
}

export function filterAndSortCompetitions(
  competitions: readonly CompetitionSummary[],
  filters: CompetitionsListFilters,
): CompetitionSummary[] {
  const query = filters.search.trim().toLowerCase();

  const filtered = competitions.filter((competition) => {
    const matchesSearch =
      query.length === 0 ||
      competition.title.toLowerCase().includes(query) ||
      competition.season.toLowerCase().includes(query) ||
      (competition.description?.toLowerCase().includes(query) ?? false);

    return matchesSearch && matchesStatusFilter(competition.status, filters.status);
  });

  return [...filtered].sort((left, right) => compareCompetitions(left, right, filters.sort));
}

function compareCompetitions(
  left: CompetitionSummary,
  right: CompetitionSummary,
  sort: CompetitionSortOption,
): number {
  if (sort === "NAME") {
    return left.title.localeCompare(right.title, "ru");
  }
  const leftTime = Date.parse(left.updatedAt);
  const rightTime = Date.parse(right.updatedAt);
  return sort === "OLDEST" ? leftTime - rightTime : rightTime - leftTime;
}
