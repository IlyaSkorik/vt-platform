import { useMemo, useState } from "react";
import {
  applyCatalog,
  type CatalogFilters,
  type CatalogSort,
  type CatalogState,
  DEFAULT_CATALOG_STATE,
  deriveFilterOptions,
  EMPTY_CATALOG_FILTERS,
  usePublicFestivals,
} from "@/features/festival-catalog";
import { CatalogError, CatalogNoFestivals, CatalogNoResults } from "./festival-catalog-states";
import { FestivalCatalogToolbar } from "./festival-catalog-toolbar";
import { FestivalFeaturedPanel } from "./festival-featured-panel";
import { FestivalFiltersPanel } from "./festival-filters-panel";
import { FestivalGrid, FestivalGridSkeleton } from "./festival-grid";

function countActiveFilters(filters: CatalogFilters): number {
  return (
    filters.registration.length +
    filters.modes.length +
    filters.categories.length +
    filters.cities.length +
    (filters.competitionFrom ? 1 : 0) +
    (filters.competitionTo ? 1 : 0)
  );
}

/**
 * The Festival Catalog — the entry point to the Participant Portal.
 *
 * One cached read backs the screen; search, filtering and sorting all run
 * client-side over the cached list, so interactions are instant and never hit
 * the network. Handles loading (skeletons), error (retry), empty and
 * no-results states explicitly.
 */
interface FestivalCatalogProps {
  detailBasePath?: string;
}

export function FestivalCatalog({
  detailBasePath = "/cabinet/competitions",
}: FestivalCatalogProps): React.JSX.Element {
  const query = usePublicFestivals();
  const festivals = query.data ?? [];

  const [now] = useState(() => new Date());
  const [state, setState] = useState<CatalogState>(DEFAULT_CATALOG_STATE);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const options = useMemo(() => deriveFilterOptions(festivals), [festivals]);
  const visible = useMemo(() => applyCatalog(festivals, state, now), [festivals, state, now]);

  const activeFilterCount = countActiveFilters(state.filters);
  const resetAll = () =>
    setState((current) => ({ ...current, query: "", filters: EMPTY_CATALOG_FILTERS }));

  if (query.isError) {
    return <CatalogError onRetry={() => query.refetch()} retrying={query.isRefetching} />;
  }

  const isLoading = query.isPending;
  const isEmpty = !isLoading && festivals.length === 0;

  if (isEmpty) {
    return <CatalogNoFestivals />;
  }

  const setQuery = (value: string) => setState((current) => ({ ...current, query: value }));
  const setSort = (sort: CatalogSort) => setState((current) => ({ ...current, sort }));
  const setFilters = (filters: CatalogFilters) => setState((current) => ({ ...current, filters }));

  return (
    <div className="space-y-5">
      <FestivalCatalogToolbar
        query={state.query}
        onQueryChange={setQuery}
        sort={state.sort}
        onSortChange={setSort}
        filtersOpen={filtersOpen}
        onToggleFilters={() => setFiltersOpen((open) => !open)}
        activeFilterCount={activeFilterCount}
      />

      {filtersOpen ? (
        <FestivalFiltersPanel
          filters={state.filters}
          options={options}
          onChange={setFilters}
          onReset={resetAll}
        />
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section aria-label="Каталог фестивалей" className="min-w-0 space-y-4">
          {!isLoading ? (
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {visible.length === festivals.length
                ? `Фестивалей: ${festivals.length}`
                : `Найдено: ${visible.length} из ${festivals.length}`}
            </p>
          ) : null}

          {isLoading ? (
            <FestivalGridSkeleton />
          ) : visible.length === 0 ? (
            <CatalogNoResults
              onReset={resetAll}
              reason={state.query.trim() ? "search" : "filters"}
            />
          ) : (
            <FestivalGrid festivals={visible} now={now} detailBasePath={detailBasePath} />
          )}
        </section>

        {!isLoading ? (
          <aside className="hidden xl:block">
            <div className="sticky top-4">
              <FestivalFeaturedPanel festivals={festivals} />
            </div>
          </aside>
        ) : null}
      </div>
    </div>
  );
}
