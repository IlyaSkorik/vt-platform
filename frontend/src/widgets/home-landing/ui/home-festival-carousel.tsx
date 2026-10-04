import { useCallback, useEffect, useRef, useState } from "react";
import type { Festival } from "@/features/festival-catalog";
import { cn } from "@/shared/lib/cn";
import { ChevronLeftIcon, ChevronRightIcon } from "@/shared/ui";
import { HomeFestivalCard } from "./home-festival-card";

interface HomeFestivalCarouselProps {
  festivals: readonly Festival[];
  /** Builds the destination for one tile. Keeps route knowledge with the page. */
  hrefFor: (festival: Festival) => string;
}

/**
 * The «Ближайшие фестивали» carousel.
 *
 * **Scrolling, not transforming.** The track is a real overflow container with
 * scroll snapping, and the arrows call `scrollBy` on it. That buys three things a
 * transform-based carousel has to re-implement badly: a trackpad swipe and a
 * touch drag work with no code at all, `Tab` into an off-screen card scrolls it
 * into view instead of stranding focus on something invisible, and the number of
 * cards per view is a CSS question (`basis-*` at each breakpoint) rather than a
 * measurement the JS has to keep in sync with the layout.
 *
 * **Paging is measured, not assumed.** How many cards share a screen is a
 * stylesheet decision (`basis-*` per breakpoint), so the JS reads it back off
 * the DOM — one card's width plus the track's own `column-gap` — and works out
 * `perView` from that. Everything else follows: the stride an arrow scrolls by,
 * how many dots there are, and which one is lit. One consequence is deliberate:
 * the dots count *screens*, so they drop from three to one as the viewport
 * widens and the same cards start fitting side by side.
 *
 * The earlier version took `pageCount` from `scrollWidth / clientWidth`, which
 * is off by the gaps: nine cards in threes measure 3.05 screens, not 3, so there
 * was always one dot that could not be reached and a «next» arrow that stayed
 * enabled at the end with nothing left to scroll to.
 */
export function HomeFestivalCarousel({
  festivals,
  hrefFor,
}: HomeFestivalCarouselProps): React.JSX.Element {
  const trackRef = useRef<HTMLUListElement>(null);
  // How far one click of an arrow travels: `perView` cards, gaps included. Held
  // in a ref rather than state because the scroll handler needs it on every
  // event and re-measuring there would force a layout per frame.
  const strideRef = useRef(0);
  // `sync` runs from a scroll event and must not close over stale state, so the
  // page count it clamps against is mirrored here alongside the stride.
  const pageCountRef = useRef(1);
  const [page, setPage] = useState(0);
  const [pageCount, setPageCount] = useState(1);

  const measure = useCallback(() => {
    const track = trackRef.current;
    const first = track?.firstElementChild;
    if (track == null || first == null || track.clientWidth === 0) {
      return;
    }
    // `column-gap` is read back rather than duplicated here, so the breakpoint
    // that changes `gap-5` to `gap-6` does not need a matching constant in JS.
    const gap = Number.parseFloat(getComputedStyle(track).columnGap) || 0;
    const slot = first.getBoundingClientRect().width + gap;
    // `+ gap` on the viewport too: the last card on a screen has no gap after
    // it, so without this the division lands just under the true count.
    const perView = Math.max(1, Math.round((track.clientWidth + gap) / slot));
    const pages = Math.max(1, Math.ceil(festivals.length / perView));
    strideRef.current = slot * perView;
    pageCountRef.current = pages;
    setPageCount(pages);
  }, [festivals.length]);

  const sync = useCallback(() => {
    const track = trackRef.current;
    const stride = strideRef.current;
    if (track == null || stride <= 0) {
      return;
    }
    const last = pageCountRef.current - 1;
    const maxScroll = track.scrollWidth - track.clientWidth;
    // The end of the track is the last page by definition, whatever the
    // arithmetic says. When the final screen is a short one — seven cards in
    // threes — the track stops a third of a stride early, and dividing would
    // report the page before it: the last dot would never light and «next»
    // would stay enabled with nowhere to go.
    setPage(
      maxScroll - track.scrollLeft <= 1
        ? last
        : Math.min(last, Math.round(track.scrollLeft / stride)),
    );
  }, []);

  // Re-measured on resize as well as on scroll: a breakpoint change alters how
  // many cards fit, and therefore how many pages exist, without any scrolling
  // happening — the dots would otherwise keep the previous layout's count.
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

  // Absolute, not relative. `scrollBy` compounds: a short last page, a snap
  // correction or a half-finished smooth scroll each leave the track a little
  // off a page boundary, and every later click inherits the error. Scrolling to
  // `page × stride` means a click always lands on the page it names.
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
  const atStart = current <= 0;
  const atEnd = current >= pageCount - 1;

  return (
    // A named `<section>` rather than a `div` with `role="group"`: the implicit
    // role a labelled section carries is `region`, which is what the APG's
    // carousel pattern asks for, and it keeps the element semantic instead of
    // bolting a role onto a generic box.
    <section aria-roledescription="карусель" aria-label="Ближайшие фестивали" className="relative">
      <div className="flex items-stretch gap-4 md:gap-6">
        <CarouselArrow
          direction="prev"
          disabled={atStart}
          className="hidden md:flex"
          onClick={() => {
            goTo(current - 1);
          }}
        />

        <ul
          ref={trackRef}
          onScroll={sync}
          // Padding on all four sides, cancelled by an equal negative margin.
          // This is what stops a card being sliced on hover. CSS gives no way to
          // scroll on one axis and overflow on the other: `overflow-x: auto`
          // forces the computed `overflow-y` to `auto` too, so this box clips in
          // every direction. A card's lift and its 26.8px glow reach outside it,
          // and the cards at the edges of the track lost theirs sideways while
          // the one in the middle kept it. The padding gives the halo room
          // *inside* the clip; the negative margin hands the space back to the
          // layout, so nothing around the carousel moves. Vertically it is
          // 40px rather than the halo's 32: a hovered card is also lifted two
          // pixels, and if the total overran the padding the track would
          // quietly become scrollable on the other axis too.
          //
          // Sideways the padding is capped at the gap between cards, and that
          // cap is the whole trick. A scroller's padding is inside the clip, so
          // whatever sits there is on show: pad wider than the gap and the next
          // card starts peeking in past the edge, which is worse than a trimmed
          // halo. At exactly the gap, a snapped card has nothing but that gap
          // beside it and its neighbour's edge falls on the clip boundary — the
          // halo gets its room and the card beyond stays hidden. At 52px
          // between cards there is room for the full 32px the halo wants, so the
          // real cap here is the page gutter — 32px in both layouts — past which
          // the glow would reach outside the container and give the page a
          // horizontal scrollbar of its own.
          className="-my-10 flex min-w-0 flex-1 snap-x snap-mandatory gap-13 overflow-x-auto py-10 [scrollbar-width:none] md:-mx-8 md:scroll-px-8 md:px-8 [&::-webkit-scrollbar]:hidden"
        >
          {festivals.map((festival) => (
            <li
              key={festival.id}
              // The basis subtracts the gaps a screen of cards carries — one
              // at `md`, two at `xl` — so `perView` cards fill the track exactly.
              // It has to be kept in step with `gap-13` above: get it wrong and
              // the last card on each screen hangs over the edge.
              className="min-w-0 shrink-0 grow-0 basis-full snap-start md:basis-[calc((100%-3.25rem)/2)] xl:basis-[calc((100%-6.5rem)/3)]"
            >
              <HomeFestivalCard festival={festival} to={hrefFor(festival)} />
            </li>
          ))}
        </ul>

        <CarouselArrow
          direction="next"
          disabled={atEnd}
          className="hidden md:flex"
          onClick={() => {
            goTo(current + 1);
          }}
        />
      </div>

      {pageCount > 1 ? (
        // On the phone the paddles live here, either side of the dots, and the
        // row is the carousel's whole control strip. `justify-between` pushes
        // them to the page gutter — 32px from each edge, against the frame's 34
        // — and because the two are the same width that also centres the dots
        // exactly, without a second centring rule to keep in step with them.
        //
        // The dots shrink with the paddles: 20px wide, 4px apart, which is the
        // frame's 20.57 and 4.12 on the nearest scale steps.
        <div className="mt-6 flex items-center justify-between gap-6 md:mt-20 md:justify-center md:gap-0">
          <CarouselArrow
            direction="prev"
            disabled={atStart}
            className="flex md:hidden"
            onClick={() => {
              goTo(current - 1);
            }}
          />
          <ul className="flex items-center justify-center gap-1 md:gap-2.5" aria-hidden="true">
            {Array.from({ length: pageCount }, (_, index) => (
              <li
                // The dots are positional markers with no identity of their own —
                // index is the only key they can have, and the list is never
                // reordered, only resized.
                // biome-ignore lint/suspicious/noArrayIndexKey: positional markers
                key={index}
                // `bg-brand` and not `bg-primary`: «Акцентище» is the lit dot in
                // both frames, and `--primary` drifts lighter at night. The rail
                // behind it is the one that changes — `светлый акцент` by day,
                // «тёмный база ночная» after dark.
                className={cn(
                  "h-[5px] w-5 transition-colors duration-[var(--duration-fast)] md:w-[50px]",
                  index === current ? "bg-brand" : "bg-brand-track",
                )}
              />
            ))}
          </ul>
          <CarouselArrow
            direction="next"
            disabled={atEnd}
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

interface CarouselArrowProps {
  direction: "prev" | "next";
  disabled: boolean;
  onClick: () => void;
  /** Which row this instance belongs to — beside the track, or under it. */
  className?: string;
}

/**
 * One of the two paddles. 70×70 beside the track on the desktop, 54×54 under it
 * on the phone, where the frame moves the pair down to flank the dots.
 *
 * Rendered twice and shown once, rather than moved by CSS: the two positions sit
 * in different parents, and faking that with `order` or absolute positioning
 * costs more than a second `<button>` that is `display: none` half the time.
 */
function CarouselArrow({
  direction,
  disabled,
  onClick,
  className,
}: CarouselArrowProps): React.JSX.Element {
  const Icon = direction === "prev" ? ChevronLeftIcon : ChevronRightIcon;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={direction === "prev" ? "Предыдущие фестивали" : "Следующие фестивали"}
      // 70×70 on a 15px corner, `светлый акцент` going to `тёмный акцент` under
      // the pointer. `--brand-control` rather than the header's
      // `--brand-surface`: the two agree in the light theme and part company
      // in the dark one, where the frame gives the paddles «светлый база
      // ночная» — greyer and lighter than the band, because here a control
      // has to stand above a near-black page instead of below a white one. The wedge is `--brand-mark` rather
      // than `--inverse`: that token flips to near-black in the dark theme,
      // where this plate is a deep violet and the arrow would have vanished.
      //
      // Spent, it says so: `cursor-not-allowed` and no hover colour. Note what
      // is *not* here — `disabled:pointer-events-none`, which used to be. With
      // pointer events off the element is invisible to the cursor and the
      // pointer stays an arrow over a button that plainly looks like one; the
      // `disabled` attribute already blocks the click on its own.
      //
      // `relative z-10` because the track's negative margin reaches back to
      // this button's edge: without it the scroll container can win the hit test
      // along the inner border and swallow the click.
      className={cn(
        "relative z-10 size-[54px] shrink-0 cursor-pointer md:size-[70px] select-none items-center justify-center self-center rounded-brand bg-brand-control text-brand-mark outline-none transition-[opacity,background-color] duration-[var(--duration-fast)] hover:bg-brand-line focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-brand-control",
        className,
      )}
    >
      <Icon className="h-8 w-5.5 md:h-10.5 md:w-7" aria-hidden="true" />
    </button>
  );
}
