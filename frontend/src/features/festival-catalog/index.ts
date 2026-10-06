/**
 * Public API of the `festival-catalog` feature.
 *
 * The participant-facing catalog's data access (TanStack Query over the public
 * read model) and framework-free domain logic (search / filter / sort, status &
 * mode presentation, formatting). Widgets compose these; nothing reaches past
 * this barrel.
 */
export { festivalCatalogKeys, usePublicFestivals } from "./api";
export {
  applyCatalog,
  type CatalogFilterOptions,
  type CatalogFilters,
  type CatalogSort,
  type CatalogState,
  type CatalogStatusConfig,
  CLOSING_SOON_DAYS,
  catalogStatusConfig,
  DEFAULT_CATALOG_STATE,
  daysUntil,
  deriveFilterOptions,
  EMPTY_CATALOG_FILTERS,
  type Festival,
  type FestivalFormat,
  type FilterOption,
  filterFestivals,
  formatDate,
  formatDeadline,
  formatPeriod,
  formatPrice,
  hasActiveFilters,
  isClosingSoon,
  isPublicStatus,
  PARTICIPATION_MODES,
  type ParticipationMode,
  type PublicStatus,
  parseApiDate,
  participationModeConfig,
  participationModeLabel,
  registrationCutoff,
  resolveMediaUrl,
  STATUS_ORDER,
  searchFestivals,
  selectFeatured,
  selectUpcoming,
  sortFestivals,
} from "./lib";
