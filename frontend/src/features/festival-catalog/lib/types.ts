import type {
  PublicFestival,
  PublicFestivalFormat,
} from "@/shared/api/generated/model-public-catalog";

/**
 * Domain types for the participant Festival Catalog.
 *
 * The wire model (`PublicFestival`, from the Orval-generated public-catalog
 * client) is used as the working view model directly — the catalog is read-only,
 * so there is no reason to remap it. These aliases give the feature a stable,
 * intention-revealing vocabulary and a single place to evolve the shape if the
 * projection and the UI ever diverge.
 */
export type Festival = PublicFestival;
export type FestivalFormat = PublicFestivalFormat;

/** Public lifecycle status projected by the backend read model. */
export type PublicStatus =
  | "COMING_SOON"
  | "REGISTRATION_OPEN"
  | "REGISTRATION_CLOSED"
  | "RUNNING"
  | "COMPLETED";

/** Normalized participation mode used for badges and filtering. */
export type ParticipationMode = "IN_PERSON" | "ONLINE" | "HYBRID";

/** Registration-oriented quick filters. */
export type RegistrationFilter = "OPEN" | "CLOSING_SOON";

/** Sort orders offered by the catalog toolbar. */
export type CatalogSort = "NEWEST" | "CLOSING_SOON" | "COMPETITION_DATE" | "ALPHABETICAL";

/**
 * The full, composable filter state.
 *
 * Every axis is additive and independent, so the shape stays future-ready: a new
 * facet is a new field plus a branch in `filterFestivals`, with no churn to the
 * existing ones. Empty arrays / nulls mean "no constraint on this axis".
 */
export interface CatalogFilters {
  registration: RegistrationFilter[];
  modes: ParticipationMode[];
  categories: string[];
  cities: string[];
  /** Inclusive competition-date window (ISO `YYYY-MM-DD`), either bound optional. */
  competitionFrom: string | null;
  competitionTo: string | null;
}

/** The complete catalog view state driven by the toolbar + filters panel. */
export interface CatalogState {
  query: string;
  sort: CatalogSort;
  filters: CatalogFilters;
}

/** An option surfaced in a filter control, derived from the loaded data. */
export interface FilterOption {
  value: string;
  count: number;
}

export const EMPTY_CATALOG_FILTERS: CatalogFilters = {
  registration: [],
  modes: [],
  categories: [],
  cities: [],
  competitionFrom: null,
  competitionTo: null,
};

export const DEFAULT_CATALOG_STATE: CatalogState = {
  query: "",
  sort: "NEWEST",
  filters: EMPTY_CATALOG_FILTERS,
};

/** Days-before-deadline window that counts as "closing soon". */
export const CLOSING_SOON_DAYS = 7;
