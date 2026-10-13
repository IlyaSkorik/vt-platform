import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/shared/lib";
import { ChevronLeftIcon, ChevronRightIcon } from "@/shared/ui";

export interface CarouselItem {
  id: string;
  content: React.ReactNode;
}

interface LandingCarouselProps {
  /** Announced as the region's name, and used for the paddles' labels. */
  label: string;
  items: CarouselItem[];
  /** Per-breakpoint width of one slide — the caller owns the layout. */
  itemClassName: string;
  /** The track's own `column-gap`; measured back off the DOM, never duplicated. */
  gapClassName: string;
  /** Air between a paddle and the track. The frame sets it per section. */
  sideGapClassName: string;
}

/**
 * The paged carousel the festival page uses for its jury and its gallery.
 *
 * Mechanically the same as the home page's: a real overflow container with
 * scroll snapping, arrows that call `scrollTo`, and a page count measured off
 * one slide's width plus the track's gap rather than assumed. That buys a
 * trackpad swipe, a touch drag and `Tab`-into-view for free, and it means the
 * number of slides per screen stays a stylesheet decision.
 *
 * It is a second implementation rather than a shared one on purpose, for now:
 * the home carousel's track carries a pile of padding/negative-margin work to
 * keep its cards' glow from being clipped, and none of that applies here —
 * these slides have no halo. Lifting one component out of the two would mean
 * carrying that machinery into a place that does not need it, or rewriting the
 * home page's carousel while its redesign is still being signed off.
 *
 * Paging is absolute (`page × stride`), not `scrollBy`: a short last page or a
 * snap correction leaves the track slightly off a boundary, and a relative
 * scroll inherits that error on every later click.
 */
export function LandingCarousel({
  label,
  items,
  itemClassName,
  gapClassName,
  sideGapClassName,
}: LandingCarouselProps): React.JSX.Element {
  const trackRef = useRef<HTMLUListElement>(null);
  // Read on every scroll event, so they live in refs: re-measuring in the
  // handler would force a layout per frame, and state would arrive stale.
  const strideRef = useRef(0);
  const pageCountRef = useRef(1);
  const [page, setPage] = useState(0);
  const [pageCount, setPageCount] = useState(1);

  const measure = useCallback(() => {
    const track = trackRef.current;
    const first = track?.firstElementChild;
    if (track == null || first == null || track.clientWidth === 0) {
      return;
    }
    const gap = Number.parseFloat(getComputedStyle(track).columnGap) || 0;
    const slot = first.getBoundingClientRect().width + gap;
    // `+ gap` on the viewport too: the last slide on a screen has no gap after
    // it, so without this the division lands just under the true count.
    const perView = Math.max(1, Math.round((track.clientWidth + gap) / slot));
    const pages = Math.max(1, Math.ceil(items.length / perView));
    strideRef.current = slot * perView;
    pageCountRef.current = pages;
    setPageCount(pages);
  }, [items.length]);

  const sync = useCallback(() => {
    const track = trackRef.current;
    const stride = strideRef.current;
    if (track == null || stride <= 0) {
      return;
    }
    const last = pageCountRef.current - 1;
    const maxScroll = track.scrollWidth - track.clientWidth;
    // The end of the track is the last page by definition: on a short final
    // screen the arithmetic reports the page before it, which would leave the
    // last dot unlit and «next» enabled with nowhere left to go.
    setPage(
      maxScroll - track.scrollLeft <= 1
        ? last
        : Math.min(last, Math.round(track.scrollLeft / stride)),
    );
  }, []);

  // Re-measured on resize as well: a breakpoint change alters how many slides
  // fit, and therefore how many pages exist, with no scrolling involved.
  useEffect(() => {
    const track = trackRef.current;
    if (track == null) {
      return;
    }
    const remeasure = (): void => {
      measure();
      sync();
    };
    remeasure();
    const observer = new ResizeObserver(remeasure);
    observer.observe(track);
    return () => {
      observer.disconnect();
    };
  }, [measure, sync]);

  const goTo = useCallback((target: number) => {
    const track = trackRef.current;
    const stride = strideRef.current;
    if (track == null || stride <= 0) {
      return;
    }
    const wanted = Math.max(0, Math.min(target, pageCountRef.current - 1));
    const maxScroll = track.scrollWidth - track.clientWidth;
    track.scrollTo({ left: Math.min(wanted * stride, maxScroll), behavior: "smooth" });
  }, []);

  // Clamped rather than trusted: a resize can shrink the page count under a
  // scroll position that was valid a moment ago.
  const current = Math.min(page, pageCount - 1);

  return (
    // A labelled `<section>` carries the `region` role the APG's carousel
    // pattern asks for, without bolting a role onto a generic box.
    <section aria-roledescription="карусель" aria-label={label}>
      <div className={cn("flex items-stretch", sideGapClassName)}>
        <CarouselPaddle
          direction="prev"
          label={label}
          disabled={current <= 0}
          className="hidden md:flex"
          onClick={() => {
            goTo(current - 1);
          }}
        />
        <ul
          ref={trackRef}
          onScroll={sync}
          className={cn(
            "flex min-w-0 flex-1 snap-x snap-mandatory overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
            gapClassName,
          )}
        >
          {items.map((item) => (
            <li key={item.id} className={cn("min-w-0 shrink-0 grow-0 snap-start", itemClassName)}>
              {item.content}
            </li>
          ))}
        </ul>
        <CarouselPaddle
          direction="next"
          label={label}
          disabled={current >= pageCount - 1}
          className="hidden md:flex"
          onClick={() => {
            goTo(current + 1);
          }}
        />
      </div>

      {pageCount > 1 ? (
        // On a phone the paddles come down here and flank the dots — the frame
        // has no room for them beside a full-width slide. Because the two are
        // the same width, `justify-between` also centres the dots exactly.
        <div className="mt-6 flex items-center justify-between gap-6 md:mt-9 md:justify-center md:gap-0">
          <CarouselPaddle
            direction="prev"
            label={label}
            disabled={current <= 0}
            className="flex md:hidden"
            onClick={() => {
              goTo(current - 1);
            }}
          />
          {/* Dashes, not dots: 50×5 with 10 between them, the frame's own rail.
              `bg-brand` for the lit one — «Акцентище» in both themes, where
              `--primary` drifts lighter at night — over `светлый акцент`. */}
          <ul className="flex items-center justify-center gap-1 md:gap-2.5" aria-hidden="true">
            {Array.from({ length: pageCount }, (_, index) => (
              <li
                // Positional markers with no identity of their own: the list is
                // never reordered, only resized.
                // biome-ignore lint/suspicious/noArrayIndexKey: positional markers
                key={index}
                className={cn(
                  "h-[5px] w-5 transition-colors duration-[var(--duration-fast)] md:w-[50px]",
                  index === current ? "bg-brand" : "bg-brand-track",
                )}
              />
            ))}
          </ul>
          <CarouselPaddle
            direction="next"
            label={label}
            disabled={current >= pageCount - 1}
            className="flex md:hidden"
            onClick={() => {
              goTo(current + 1);
            }}
          />
        </div>
      ) : null}
    </section>
  );
}

interface CarouselPaddleProps {
  direction: "prev" | "next";
  label: string;
  disabled: boolean;
  onClick: () => void;
  /** Which row this instance belongs to — beside the track, or under it. */
  className?: string;
}

/**
 * One of the two paddles: 69×69 beside the track on a desktop, 54×54 under it
 * on a phone. Rendered twice and shown once, because the two positions sit in
 * different parents and faking that with `order` costs more than a second
 * button that is `display: none` half the time.
 *
 * Spent, it says so — `cursor-not-allowed` and no hover colour, and
 * deliberately no `disabled:pointer-events-none`: with pointer events off the
 * cursor stays an arrow over something that plainly looks like a button, and
 * the `disabled` attribute already blocks the click.
 */
function CarouselPaddle({
  direction,
  label,
  disabled,
  onClick,
  className,
}: CarouselPaddleProps): React.JSX.Element {
  const Icon = direction === "prev" ? ChevronLeftIcon : ChevronRightIcon;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={`${direction === "prev" ? "Назад" : "Вперёд"}: ${label}`}
      className={cn(
        "size-[54px] shrink-0 cursor-pointer select-none items-center justify-center self-center rounded-brand bg-brand-control text-brand-mark outline-none transition-[opacity,background-color] duration-[var(--duration-fast)] hover:bg-brand-press focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-brand-control md:size-[69px]",
        className,
      )}
    >
      <Icon className="h-8 w-5.5 md:h-[27px] md:w-[22px]" aria-hidden="true" />
    </button>
  );
}
