import { useEffect, useMemo, useState } from "react";
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
import { FestivalCatalogPagination } from "./festival-catalog-pagination";
import { CatalogError, CatalogNoFestivals, CatalogNoResults } from "./festival-catalog-states";
import { FestivalCatalogToolbar } from "./festival-catalog-toolbar";
import { FestivalFiltersSidebar } from "./festival-filters-sidebar";
import { FestivalGrid, FestivalGridSkeleton } from "./festival-grid";

/**
 * Cards per page.
 *
 * Six, which is three rows of the frame's two columns. The number is a layout
 * decision rather than a data one — the whole catalogue is already in memory,
 * and paging exists so a reader meets the list in screenfuls instead of
 * scrolling past forty cards to reach the filters they wanted to change.
 */
const PAGE_SIZE = 6;

/**
 * The Festival Catalog — the entry point to the Participant Portal.
 *
 * One cached read backs the screen; search, filtering, sorting and paging all
 * run client-side over that list, so interactions are instant and never hit the
 * network. Handles loading (skeletons), error (retry), empty and no-results
 * states explicitly.
 *
 * **Filters stand to the left rather than opening over the grid.** They are the
 * reason this page is not the landing's carousel: a visitor arrives knowing a
 * genre or a city, and a panel they have to open first hides that the catalogue
 * can be narrowed at all.
 */
interface FestivalCatalogProps {
  detailBasePath?: string;
  /**
   * The page's own heading, rendered at the top of the results column.
   *
   * It lives here rather than above the widget because the frame sets it level
   * with the top of the filters panel and flush with the grid, not across the
   * page — a title over both columns reads as a heading for the filters too. The
   * cabinet omits it and keeps its own page header.
   */
  title?: string;
}

export function FestivalCatalog({
  detailBasePath = "/cabinet/competitions",
  title,
}: FestivalCatalogProps): React.JSX.Element {
  const query = usePublicFestivals();
  const festivals = query.data ?? [];

  const [now] = useState(() => new Date());
  const [state, setState] = useState<CatalogState>(DEFAULT_CATALOG_STATE);
  const [page, setPage] = useState(1);

  const options = useMemo(() => deriveFilterOptions(festivals), [festivals]);
  const visible = useMemo(() => applyCatalog(festivals, state, now), [festivals, state, now]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  // Narrowing the list can strand the reader on a page that no longer exists —
  // page 7 of a catalogue that is now four pages long renders nothing at all.
  // Clamping on render would fight the click that caused it, so the correction
  // happens after, and only when it is needed.
  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);
  const current = Math.min(page, pageCount);
  const pageItems = visible.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  // Paging without this leaves the reader looking at the bottom of a page they
  // have not seen the top of: the grid is three rows tall and the strip they
  // clicked is below all of it. `smooth` rather than an instant jump so the move
  // reads as the same page scrolling, not as a navigation; the global
  // reduced-motion reset turns it back into a jump for anyone who asked.
  const goToPage = (next: number) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const resetAll = () =>
    setState((currentState) => ({ ...currentState, query: "", filters: EMPTY_CATALOG_FILTERS }));

  if (query.isError) {
    return <CatalogError onRetry={() => query.refetch()} retrying={query.isRefetching} />;
  }

  const isLoading = query.isPending;

  if (!isLoading && festivals.length === 0) {
    return <CatalogNoFestivals />;
  }

  // Every change to what is shown sends the reader back to the first page. The
  // alternative — keeping the page number across a new search — lands them in
  // the middle of a result set they have not seen the start of.
  const setQuery = (value: string) => {
    setState((currentState) => ({ ...currentState, query: value }));
    setPage(1);
  };
  const setSort = (sort: CatalogSort) => setState((currentState) => ({ ...currentState, sort }));
  const setFilters = (filters: CatalogFilters) => {
    setState((currentState) => ({ ...currentState, filters }));
    setPage(1);
  };

  return (
    // A grid rather than a row, because the two layouts put these three blocks in
    // different orders. On a phone the frame stacks them: search and sort, then
    // the filters, then the results — filters sit *between* the controls and what
    // they filter, which is where a tray belongs. From `xl` the filters become a
    // standing column beside both, so they are placed into column one across both
    // rows while the header and the results keep column two.
    //
    // Explicit placement and not a reordered flex row: DOM order stays the
    // phone's, which is the order a screen reader should hear either way.
    //
    // The rows are not evenly spaced on a phone: 16px runs down the controls —
    // search to sort, sort to filters — and 30 falls between the filters and the
    // first card. The grid carries the 16 and the results block adds the
    // remaining 14, because a grid has one gap and these two are different
    // distances: inside a group of controls, and between that group and what it
    // acts on.
    <div className="grid gap-4 xl:grid-cols-[413px_minmax(0,1fr)] xl:gap-x-[13px]">
      <div className="min-w-0 space-y-4 xl:col-start-2 xl:row-start-1">
        {title ? (
          // `sr-only` and not `hidden` on the phone, where the frame drops the
          // title: the page still needs a heading — it is the only thing naming
          // what this screen is to a screen reader, and to search. Visually the
          // band under it says the same in three words, which is why the frame
          // can spend the space on a card instead.
          <h1 className="sr-only font-heading font-bold text-foreground leading-snug tracking-tight xl:not-sr-only xl:text-[1.75rem]">
            {title}
          </h1>
        ) : null}

        <FestivalCatalogToolbar
          query={state.query}
          onQueryChange={setQuery}
          sort={state.sort}
          onSortChange={setSort}
        />
      </div>

      <FestivalFiltersSidebar
        filters={state.filters}
        options={options}
        onChange={setFilters}
        className="xl:col-start-1 xl:row-start-1 xl:row-end-3"
      />

      <section
        aria-label="Каталог фестивалей"
        className="mt-[14px] min-w-0 space-y-4 xl:col-start-2 xl:row-start-2 xl:mt-0"
      >
        {isLoading ? (
          <FestivalGridSkeleton />
        ) : visible.length === 0 ? (
          <CatalogNoResults onReset={resetAll} reason={state.query.trim() ? "search" : "filters"} />
        ) : (
          // 23px from the last card to the pagination, as the frame measures it.
          // A wrapper rather than a margin on the strip itself: the section's own
          // `space-y` sets `margin-top` through a selector that outranks a plain
          // `mt-*` on a child, so the two would have fought and the selector would
          // have won.
          <div className="space-y-[23px]">
            <FestivalGrid festivals={pageItems} now={now} detailBasePath={detailBasePath} />
            {/* Announced rather than drawn: the frame has no result count, but a
                reader who narrows the list with a screen reader otherwise gets no
                confirmation that anything happened. */}
            <p className="sr-only" aria-live="polite">
              {visible.length === festivals.length
                ? `Фестивалей: ${festivals.length}`
                : `Найдено: ${visible.length} из ${festivals.length}`}
            </p>
            <FestivalCatalogPagination
              page={current}
              pageCount={pageCount}
              onPageChange={goToPage}
            />
          </div>
        )}
      </section>
    </div>
  );
}
