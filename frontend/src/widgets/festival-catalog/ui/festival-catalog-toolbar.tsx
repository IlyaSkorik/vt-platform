import { Check, ChevronUp } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { CatalogSort } from "@/features/festival-catalog";
import { cn } from "@/shared/lib";
import { SearchIcon } from "@/shared/ui";

// `as const` so the tuple is known to be non-empty: the lookup below falls back
// to the first entry, and without it that fallback is itself `undefined`.
const SORT_OPTIONS = [
  { value: "NEWEST", label: "Сначала новые" },
  { value: "COMPETITION_DATE", label: "По дате проведения" },
  { value: "ALPHABETICAL", label: "По алфавиту" },
] as const satisfies readonly { value: CatalogSort; label: string }[];

interface SortMenuProps {
  sort: CatalogSort;
  onSortChange: (sort: CatalogSort) => void;
}

/**
 * The sort control, built here rather than taken from `shared/ui`'s `Select`.
 *
 * The frame draws it as a label on the band with a panel that opens *below* the
 * band and over the grid — `свет` on a «тёмный акцент» hairline, its rows at a
 * 5px corner, the current one washed in «светлый акцент» at half strength. A
 * native select cannot be painted that way, and the shared `Select` is styled
 * for forms, where it belongs; dressing it up for one band would have left every
 * form on the product wearing the landing's clothes.
 */
function SortMenu({ sort, onSortChange }: SortMenuProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const current = SORT_OPTIONS.find((option) => option.value === sort) ?? SORT_OPTIONS[0];

  // Closing on an outside click and on Escape, because this is a menu and not a
  // disclosure: leaving it open while the reader moves on is how a dropdown ends
  // up covering the thing it was meant to sort.
  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: PointerEvent): void => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        className="flex h-[41px] w-full cursor-pointer items-center justify-between gap-2 rounded-brand border-4 border-brand-surface bg-background px-4 font-heading text-base text-foreground outline-none transition-colors hover:bg-background/80 focus-visible:ring-2 focus-visible:ring-ring xl:h-6 xl:w-[211px] xl:border-0 xl:px-[15px] xl:text-xs dark:border-brand-line/70 xl:dark:border-transparent"
      >
        <span className="truncate">{current.label}</span>
        <ChevronUp
          className={cn("size-5 shrink-0 transition-transform xl:size-3.5", !open && "rotate-180")}
          aria-hidden="true"
        />
      </button>

      {open ? (
        <ul
          id={menuId}
          // 3px below the trigger and 9px of padding inside, as the frame has it:
          // the panel is meant to read as the trigger's own drawer rather than as
          // a card that happens to be near it.
          //
          // `z-10` and not a portal: it only ever has to clear the grid directly
          // beneath, and a portal would cost the outside-click handling above its
          // one simple containment check.
          className="absolute top-[calc(100%+3px)] right-0 left-0 z-10 space-y-1.5 rounded-brand border border-brand-line bg-background p-[9px] shadow-elevation-2 xl:left-auto xl:w-[211px]"
        >
          {SORT_OPTIONS.map((option) => {
            const active = option.value === sort;
            return (
              <li key={option.value}>
                <button
                  type="button"
                  onClick={() => {
                    onSortChange(option.value);
                    setOpen(false);
                  }}
                  aria-current={active}
                  className={cn(
                    "flex h-[30px] w-full cursor-pointer items-center justify-between gap-2 rounded-[5px] px-2 text-left font-heading text-foreground text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring xl:text-xs",
                    active
                      ? "bg-brand-line-soft/50 dark:bg-brand-control/60"
                      : "hover:bg-brand-line-soft/25 dark:hover:bg-brand-control/30",
                  )}
                >
                  <span className="truncate">{option.label}</span>
                  {active ? <Check className="size-3.5 shrink-0" aria-hidden="true" /> : null}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

interface FestivalCatalogToolbarProps {
  query: string;
  onQueryChange: (query: string) => void;
  sort: CatalogSort;
  onSortChange: (sort: CatalogSort) => void;
}

/**
 * The band over the grid: search on the left, sort on the right, both sitting on
 * a solid strip of «светлый акцент».
 *
 * On a phone the sort control leaves the band and stands on its own, ringed in
 * four pixels of the same violet the band is painted with — «светлый акцент» by
 * day, «тёмный акцент» at 70% by night. It is 41px there against the bands' 48,
 * which is what keeps the three rows from reading as one striped block.
 *
 * The strip is the control, not a container for controls — which is why the
 * search field is a bare input on `свет` rather than `shared/ui`'s `Input`. That
 * component carries a border, a focus ring and a label slot, all of which fight
 * a field whose whole job is to be a hole in a coloured band.
 *
 * The placeholder is Noto Serif 12/16 on a desktop and 16/22 on a phone — the
 * field is 30px tall in both, and the desktop's longer band gives the label room
 * to be small without crowding. The typed text takes the same size as the
 * placeholder; a field whose hint and content are set differently reads as two
 * controls.
 *
 * The band's own insets are stated rather than left to `items-center`: 10px top
 * and bottom, 23 from the left edge to the field, 26 from the field across to the
 * sort control. The field is the 28px those leave inside a 48px band, written
 * out rather than taken as `h-full`: it sits inside a `label` with no height of
 * its own, so the percentage had nothing to resolve against and collapsed to the
 * height of the text — a 16px strip where a field should be.
 *
 * The frame prints the placeholder the same
 * `#A9A9A8` in both themes — a mid grey that happens to sit over `свет` and over
 * the night page alike. It is reached from either side rather than frozen as a
 * hex: the page's own ink at 37% by day, `свет` at 65% by night. Both land on
 * that value over their own background, and both keep working if the background
 * is ever retuned, which a hex would not.
 *
 * Not `--muted-foreground`, which is `--neutral-500` — a violet-tinted grey built
 * for body copy, and markedly darker than this.
 */
export function FestivalCatalogToolbar({
  query,
  onQueryChange,
  sort,
  onSortChange,
}: FestivalCatalogToolbarProps): React.JSX.Element {
  return (
    // Stacked on a phone, one row on a desktop. The band holds only the search
    // there — at 375px a 211px sort control beside a 291px field does not fit,
    // and the frame drops it onto a line of its own rather than shrinking both
    // into illegibility.
    <div className="space-y-4 xl:space-y-0">
      <div className="flex h-12 items-center gap-2 rounded-brand bg-brand-surface px-2 py-2.5 xl:gap-[26px] xl:pr-6 xl:pl-[23px] dark:bg-brand-line/70 xl:dark:bg-brand-surface">
        <label className="flex min-w-0 flex-1 items-center gap-2 xl:gap-3">
          <span className="sr-only">Поиск фестивалей</span>
          <input
            type="search"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Найти фестиваль"
            className="h-7 w-full min-w-0 rounded-brand bg-background px-4 font-heading text-base text-foreground leading-snug outline-none transition-shadow placeholder:text-foreground/37 dark:placeholder:text-on-scrim/65 focus-visible:ring-2 focus-visible:ring-ring xl:max-w-[336px] xl:text-xs xl:leading-4 [&::-webkit-search-cancel-button]:hidden"
          />
          <SearchIcon className="size-7 shrink-0 text-brand-mark xl:h-[26px] xl:w-[25px]" />
        </label>

        <div className="hidden xl:block">
          <SortMenu sort={sort} onSortChange={onSortChange} />
        </div>
      </div>

      <div className="xl:hidden">
        <SortMenu sort={sort} onSortChange={onSortChange} />
      </div>
    </div>
  );
}
