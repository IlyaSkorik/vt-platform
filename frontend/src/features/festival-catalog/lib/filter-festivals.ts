import { parseApiDate, registrationCutoff } from "./format";
import type {
  CatalogFilters,
  CatalogSort,
  CatalogState,
  Festival,
  FilterOption,
  PublicStatus,
} from "./types";
import { STATUS_ORDER } from "./types";

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

/** Text a search query is matched against: title, city, organizer, categories. */
function searchHaystack(festival: Festival): string {
  return normalize(
    [festival.title, festival.city ?? "", festival.organizer.name, ...festival.categories].join(
      " ",
    ),
  );
}

/**
 * Live search across title, city and organizer name.
 *
 * Every whitespace-separated term must appear somewhere in the haystack (AND),
 * so "минск вокал" narrows rather than widens. An empty query matches all.
 */
export function searchFestivals(festivals: Festival[], query: string): Festival[] {
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  if (terms.length === 0) {
    return festivals;
  }
  return festivals.filter((festival) => {
    const haystack = searchHaystack(festival);
    return terms.every((term) => haystack.includes(term));
  });
}

function matchesStatuses(festival: Festival, filters: CatalogFilters): boolean {
  if (filters.statuses.length === 0) {
    return true;
  }
  return filters.statuses.includes(festival.status as PublicStatus);
}

function matchesModes(festival: Festival, filters: CatalogFilters): boolean {
  if (filters.modes.length === 0) {
    return true;
  }
  return filters.modes.some((mode) => festival.modes.includes(mode));
}

function matchesCategories(festival: Festival, filters: CatalogFilters): boolean {
  if (filters.categories.length === 0) {
    return true;
  }
  return filters.categories.some((category) => festival.categories.includes(category));
}

function matchesCities(festival: Festival, filters: CatalogFilters): boolean {
  if (filters.cities.length === 0) {
    return true;
  }
  return festival.city != null && filters.cities.includes(festival.city);
}

function matchesDateWindow(festival: Festival, filters: CatalogFilters): boolean {
  const { competitionFrom, competitionTo } = filters;
  if (!competitionFrom && !competitionTo) {
    return true;
  }
  const start = parseApiDate(festival.competitionStart)?.getTime() ?? null;
  const end = parseApiDate(festival.competitionEnd)?.getTime() ?? start;
  if (start == null && end == null) {
    return false;
  }
  const from = parseApiDate(competitionFrom)?.getTime() ?? null;
  const to = parseApiDate(competitionTo)?.getTime() ?? null;
  const periodEnd = end ?? start;
  const periodStart = start ?? end;
  if (from != null && periodEnd != null && periodEnd < from) {
    return false;
  }
  if (to != null && periodStart != null && periodStart > to) {
    return false;
  }
  return true;
}

/** Apply every filter axis (all axes ANDed; options within an axis ORed). */
export function filterFestivals(festivals: Festival[], filters: CatalogFilters): Festival[] {
  return festivals.filter(
    (festival) =>
      matchesStatuses(festival, filters) &&
      matchesModes(festival, filters) &&
      matchesCategories(festival, filters) &&
      matchesCities(festival, filters) &&
      matchesDateWindow(festival, filters),
  );
}

function time(value: string | null | undefined): number | null {
  return parseApiDate(value)?.getTime() ?? null;
}

/** Ascending comparator that always sorts `null` to the end. */
function ascNullsLast(a: number | null, b: number | null): number {
  if (a == null && b == null) {
    return 0;
  }
  if (a == null) {
    return 1;
  }
  if (b == null) {
    return -1;
  }
  return a - b;
}

/** Where a festival sits in `STATUS_ORDER`; anything unknown goes to the end. */
function statusRank(festival: Festival): number {
  const index = STATUS_ORDER.indexOf(festival.status as PublicStatus);
  return index === -1 ? STATUS_ORDER.length : index;
}

export function sortFestivals(festivals: Festival[], sort: CatalogSort): Festival[] {
  const sorted = [...festivals];
  switch (sort) {
    // The default, and the only sort that groups by status first: a catalogue
    // whose first screen is finished festivals is useless however new they are,
    // so recency orders *within* what you can still do something about. The other
    // sorts mean exactly what they say — an alphabetical list broken into status
    // groups is not alphabetical.
    case "NEWEST":
      sorted.sort(
        (a, b) =>
          statusRank(a) - statusRank(b) || ascNullsLast(time(b.createdAt), time(a.createdAt)),
      );
      break;
    case "CLOSING_SOON":
      sorted.sort((a, b) => ascNullsLast(time(registrationCutoff(a)), time(registrationCutoff(b))));
      break;
    case "COMPETITION_DATE":
      sorted.sort((a, b) => ascNullsLast(time(a.competitionStart), time(b.competitionStart)));
      break;
    case "ALPHABETICAL":
      sorted.sort((a, b) => a.title.localeCompare(b.title, "ru"));
      break;
  }
  return sorted;
}

/**
 * Run the full pipeline: search → filter → sort.
 *
 * `now` is still taken, and still unused by the filters: every axis is a property
 * of the festival itself since the registration window stopped being one of them.
 * Kept because the caller holds a frozen clock for the whole render and a time
 * axis is the obvious next one to add.
 */
export function applyCatalog(festivals: Festival[], state: CatalogState, _now: Date): Festival[] {
  const searched = searchFestivals(festivals, state.query);
  const filtered = filterFestivals(searched, state.filters);
  return sortFestivals(filtered, state.sort);
}

function countBy(festivals: Festival[], values: (festival: Festival) => string[]): FilterOption[] {
  const counts = new Map<string, number>();
  for (const festival of festivals) {
    for (const value of values(festival)) {
      if (value) {
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }
    }
  }
  return [...counts.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => a.value.localeCompare(b.value, "ru"));
}

/** Filter option lists derived from the loaded data (future-ready, data-driven). */
export interface CatalogFilterOptions {
  statuses: FilterOption[];
  cities: FilterOption[];
  categories: FilterOption[];
}

export function deriveFilterOptions(festivals: Festival[]): CatalogFilterOptions {
  // Statuses are offered in `STATUS_ORDER` and only when the catalogue actually
  // holds one — a checkbox for «Фестиваль завершён» on a list with none is a
  // promise of results that do not exist. Cities and categories are counted the
  // same way, alphabetically; a status list sorted by name would read as noise.
  const present = new Set(festivals.map((festival) => festival.status));
  return {
    statuses: STATUS_ORDER.filter((status) => present.has(status)).map((status) => ({
      value: status,
      count: festivals.filter((festival) => festival.status === status).length,
    })),
    cities: countBy(festivals, (festival) => (festival.city ? [festival.city] : [])),
    categories: countBy(festivals, (festival) => festival.categories),
  };
}

/** True when any filter axis constrains the result (drives the "reset" affordance). */
export function hasActiveFilters(filters: CatalogFilters): boolean {
  return (
    filters.statuses.length > 0 ||
    filters.modes.length > 0 ||
    filters.categories.length > 0 ||
    filters.cities.length > 0 ||
    filters.competitionFrom != null ||
    filters.competitionTo != null
  );
}
