import { cn } from "@/shared/lib";
import { ChevronLeftIcon, ChevronRightIcon } from "@/shared/ui";

/**
 * The page numbers to draw, with `null` standing for an elision.
 *
 * Always the first page, the last, and the current with a neighbour either side.
 * The rule is about the *reader's* reach rather than about fitting a width: from
 * any page they can get to the ends, step one at a time, or jump — and the strip
 * never changes length as they move through it, which is what makes the control
 * stop twitching under the cursor.
 */
function pageItems(current: number, total: number): (number | null)[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1);
  }
  const items: (number | null)[] = [1];
  const from = Math.max(2, current - 1);
  const to = Math.min(total - 1, current + 1);
  if (from > 2) {
    items.push(null);
  }
  for (let page = from; page <= to; page += 1) {
    items.push(page);
  }
  if (to < total - 1) {
    items.push(null);
  }
  items.push(total);
  return items;
}

interface PaddleProps {
  direction: "prev" | "next";
  disabled: boolean;
  onClick: () => void;
}

function Paddle({ direction, disabled, onClick }: PaddleProps): React.JSX.Element {
  const Icon = direction === "prev" ? ChevronLeftIcon : ChevronRightIcon;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={direction === "prev" ? "Предыдущая страница" : "Следующая страница"}
      // The carousel's paddle at the catalogue's size: 54px on the brand's 15px
      // corner, `светлый акцент` by day and the night base after dark, which is
      // what `--brand-control` already resolves to. Spent, it says so rather
      // than disappearing — `cursor-not-allowed` and no hover colour, and
      // deliberately no `pointer-events-none`, which would make the cursor blind
      // to a button that still plainly looks like one.
      className="flex size-[54px] shrink-0 cursor-pointer items-center justify-center rounded-brand bg-brand-control text-brand-mark outline-none transition-[opacity,background-color] duration-[var(--duration-fast)] hover:bg-brand-line focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-brand-control"
    >
      <Icon className="h-8 w-5.5" aria-hidden="true" />
    </button>
  );
}

interface FestivalCatalogPaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}

/**
 * The numbered strip under the grid, with a paddle at each end.
 *
 * On a phone the two paddles are pushed to the edges and the numbers sit between
 * them — 29px in from the screen, which is the page's own 14px gutter plus 15
 * here. Thumbs reach the sides of a phone and not its middle, so the two controls
 * that are pressed repeatedly go where the thumb already is. On a desktop the
 * whole strip is centred instead, because there it is read before it is clicked.
 */
export function FestivalCatalogPagination({
  page,
  pageCount,
  onPageChange,
}: FestivalCatalogPaginationProps): React.JSX.Element | null {
  if (pageCount <= 1) {
    return null;
  }

  return (
    <nav
      aria-label="Страницы каталога"
      className="flex items-center justify-between gap-2 px-[15px] xl:justify-center xl:gap-5 xl:px-0"
    >
      <Paddle direction="prev" disabled={page <= 1} onClick={() => onPageChange(page - 1)} />

      <ul className="flex items-center gap-1">
        {pageItems(page, pageCount).map((item, index) =>
          item === null ? (
            <li
              // Two elisions can appear, and neither has an identity beyond its
              // place in the strip.
              // biome-ignore lint/suspicious/noArrayIndexKey: positional marker
              key={`gap-${index}`}
              aria-hidden="true"
              className="flex size-[49px] items-center justify-center font-heading text-2xl text-foreground/70 leading-snug"
            >
              …
            </li>
          ) : (
            <li key={item}>
              <button
                type="button"
                onClick={() => onPageChange(item)}
                aria-current={item === page ? "page" : undefined}
                aria-label={`Страница ${item}`}
                // Three states, and the frame's own reading of them. The page you
                // are *on* is the quiet one — a hairline at 40% around a number
                // at 40% — because it is where you already are and does not need
                // to be sold. The pointer is what is loud: a two-pixel «тёмный
                // акцент» at 66% and the number at full strength. Everything else
                // sits between the two at 70%.
                //
                // At night both lines are brighter, because the plate under them
                // is: the current page is ringed in «свет» at 70% and the pointer
                // in «Акцентище» itself, which on a near-black page is the one
                // violet that still reads as lit.
                //
                // The border is on the box at all three, transparent where it is
                // not drawn, so hovering thickens a line rather than adding one
                // and the strip does not jump under the cursor.
                className={cn(
                  "flex h-[47px] w-[49px] cursor-pointer items-center justify-center rounded-[14px] border font-heading text-2xl leading-snug outline-none transition-colors hover:border-2 hover:border-brand-line/66 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring dark:hover:border-brand",
                  item === page
                    ? "border-foreground/40 text-foreground/40 dark:border-on-scrim-muted"
                    : "border-transparent text-foreground/70",
                )}
              >
                {item}
              </button>
            </li>
          ),
        )}
      </ul>

      <Paddle
        direction="next"
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      />
    </nav>
  );
}
