import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
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
  /**
   * Extra classes for the scrolling track itself — side padding, mostly.
   * Padding is how a strip is centred: a flex container that overflows cannot
   * be `justify-center` without clipping its own first item, so the slide is
   * brought to the middle by leaving half the leftover width either side of
   * it instead.
   */
  trackClassName?: string;
  /**
   * Where the paddles and the dash rail appear. `"md-up"` hides both on a
   * phone, where the frame leaves the gallery as a bare strip of pictures.
   */
  controls?: "always" | "md-up";
  /**
   * Creep sideways on a phone, endlessly, while nobody is touching it.
   *
   * Only where the controls are hidden: a track that moves on its own *and*
   * has arrows fights the reader for the same slide.
   */
  drift?: boolean;
}

/** Pixels per second the drifting track travels. Slow enough to read past. */
const DRIFT_SPEED = 30;

/** How long after a touch the drift waits before picking up again. */
const DRIFT_RESUME_MS = 3500;

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
  trackClassName,
  controls = "always",
  drift = false,
}: LandingCarouselProps): React.JSX.Element {
  const trackRef = useRef<HTMLUListElement>(null);
  // Everything the scroll handler needs lives in a ref, because reading any of
  // it off the DOM there would force a layout on every frame of a scroll.
  const strideRef = useRef(0);
  const slotRef = useRef(0);
  const pageCountRef = useRef(1);
  // The scrollable distance, measured once per layout instead of per event.
  // `scrollWidth` is the expensive read — asking for it mid-scroll made the
  // browser re-lay-out the whole track, every frame, while it was animating.
  const maxScrollRef = useRef(0);
  // The page the dots are already showing. Compared against before touching
  // state, so a scroll across one screen schedules one render rather than the
  // sixty React would otherwise bail out of one at a time.
  const pageRef = useRef(0);
  // Set while a measurement is queued, so a burst of scroll events collapses
  // into a single read at the next frame.
  const frameRef = useRef<number | null>(null);
  const [page, setPage] = useState(0);
  const [pageCount, setPageCount] = useState(1);
  // How many slides have already been carried round to the back of the queue.
  // The drifting track never runs out: when the leading slide has scrolled out
  // of sight it is moved to the end and the scroll position is pulled back by
  // exactly its width, so the strip is endless with one copy of each picture.
  // Rotating the data rather than rendering the list twice keeps every tile
  // real — a duplicated strip has to be `aria-hidden`, and then half the
  // pictures on screen are not clickable and not announced.
  const [rotation, setRotation] = useState(0);
  // Set between deciding to rotate and the layout effect that compensates the
  // scroll for it, so the two happen in one frame and nothing visibly jumps.
  const pendingRotation = useRef(0);
  // The drift's own position, in fractions of a pixel.
  //
  // It cannot live in `scrollLeft`: that property rounds, and at 28 px/s a
  // frame is under half a pixel — `scrollLeft += 0.46` rounded straight back
  // to where it started, every frame, so the strip sat still. Accumulating
  // here and *assigning* the total is what makes a slow drift possible at all.
  const positionRef = useRef(0);
  const [drifting, setDrifting] = useState(false);

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
    slotRef.current = slot;
    strideRef.current = slot * perView;
    pageCountRef.current = pages;
    maxScrollRef.current = track.scrollWidth - track.clientWidth;
    setPageCount(pages);
  }, [items.length]);

  /** Which page the track is on right now. Reads `scrollLeft` and nothing else. */
  const read = useCallback(() => {
    const track = trackRef.current;
    const stride = strideRef.current;
    if (track == null || stride <= 0) {
      return;
    }
    const last = pageCountRef.current - 1;
    // The end of the track is the last page by definition: on a short final
    // screen the arithmetic reports the page before it, which would leave the
    // last dot unlit and «next» enabled with nowhere left to go.
    const next =
      maxScrollRef.current - track.scrollLeft <= 1
        ? last
        : Math.min(last, Math.round(track.scrollLeft / stride));
    if (next !== pageRef.current) {
      pageRef.current = next;
      setPage(next);
    }
  }, []);

  // One read per animation frame, however many scroll events arrive in it.
  const sync = useCallback(() => {
    if (frameRef.current != null) {
      return;
    }
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null;
      read();
    });
  }, [read]);

  // Re-measured on resize as well: a breakpoint change alters how many slides
  // fit, and therefore how many pages exist, with no scrolling involved.
  useEffect(() => {
    const track = trackRef.current;
    if (track == null) {
      return;
    }
    const remeasure = (): void => {
      measure();
      read();
    };
    remeasure();
    const observer = new ResizeObserver(remeasure);
    observer.observe(track);
    return () => {
      observer.disconnect();
      if (frameRef.current != null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
    };
  }, [measure, read]);

  // Drift only below `md`, and only if the reader has not asked for less
  // motion: a strip that moves by itself with no way to stop it is exactly
  // what `prefers-reduced-motion` is about.
  useEffect(() => {
    if (!drift) {
      return;
    }
    const narrow = window.matchMedia("(max-width: 767px)");
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = (): void => {
      setDrifting(narrow.matches && !calm.matches);
    };
    update();
    narrow.addEventListener("change", update);
    calm.addEventListener("change", update);
    return () => {
      narrow.removeEventListener("change", update);
      calm.removeEventListener("change", update);
    };
  }, [drift]);

  // The drift itself. Nothing is measured inside the loop — the slide's width
  // comes from the last layout pass — so a frame costs an assignment and a
  // comparison. A touch, a drag or a wheel stops it for a few seconds: the
  // reader's gesture always wins over the animation.
  useEffect(() => {
    const track = trackRef.current;
    if (!drifting || track == null) {
      return;
    }
    let frame = 0;
    let previous = 0;
    let heldUntil = 0;
    positionRef.current = track.scrollLeft;
    const tick = (now: number): void => {
      frame = requestAnimationFrame(tick);
      const elapsed = previous === 0 ? 0 : (now - previous) / 1000;
      previous = now;
      // Held: the reader is dragging, so the track's position is theirs. Keep
      // ours in step with it, or the drift would snap back to where it left
      // off the moment it resumes.
      if (now < heldUntil) {
        positionRef.current = track.scrollLeft;
        return;
      }
      // A rotation is queued but the list has not re-rendered yet. Moving now
      // would shift the strip before the slide behind it had moved, which is
      // the one-slide jump the layout effect exists to prevent.
      if (pendingRotation.current > 0) {
        return;
      }
      positionRef.current += DRIFT_SPEED * elapsed;
      track.scrollLeft = positionRef.current;
      const slot = slotRef.current;
      // The leading slide has gone: carry it to the back and pull the scroll
      // position back by its width in the same frame — see `rotation`.
      if (slot > 0 && positionRef.current >= slot) {
        pendingRotation.current += 1;
        setRotation((value) => value + 1);
      }
    };
    const hold = (): void => {
      heldUntil = performance.now() + DRIFT_RESUME_MS;
    };
    track.addEventListener("pointerdown", hold);
    track.addEventListener("touchstart", hold, { passive: true });
    track.addEventListener("wheel", hold, { passive: true });
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      track.removeEventListener("pointerdown", hold);
      track.removeEventListener("touchstart", hold);
      track.removeEventListener("wheel", hold);
    };
  }, [drifting]);

  // Before the browser paints the rotated list, take back the distance the
  // slide that moved to the end was occupying. In an effect that runs after
  // paint this is a visible jump of one slide, every slide.
  //
  // `rotation` is named as a dependency even though the body never reads it:
  // it is the trigger, and the correction has to run exactly once per rotation.
  // biome-ignore lint/correctness/useExhaustiveDependencies: trigger, not input
  useLayoutEffect(() => {
    const track = trackRef.current;
    if (track == null || pendingRotation.current === 0) {
      return;
    }
    track.scrollLeft -= slotRef.current * pendingRotation.current;
    positionRef.current = track.scrollLeft;
    pendingRotation.current = 0;
  }, [rotation]);

  const goTo = useCallback((target: number) => {
    const track = trackRef.current;
    const stride = strideRef.current;
    if (track == null || stride <= 0) {
      return;
    }
    const wanted = Math.max(0, Math.min(target, pageCountRef.current - 1));
    track.scrollTo({ left: Math.min(wanted * stride, maxScrollRef.current), behavior: "smooth" });
  }, []);

  // Clamped rather than trusted: a resize can shrink the page count under a
  // scroll position that was valid a moment ago.
  const current = Math.min(page, pageCount - 1);
  const shown =
    rotation === 0
      ? items
      : [...items.slice(rotation % items.length), ...items.slice(0, rotation % items.length)];

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
            "flex min-w-0 flex-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
            // Snapping and drifting cannot both have the scroll position:
            // mandatory snap drags the track back to the nearest slide on every
            // frame the drift nudges it forward.
            drifting ? "snap-none" : "snap-x snap-mandatory",
            gapClassName,
            trackClassName,
          )}
        >
          {shown.map((item) => (
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
        <div
          className={cn(
            "mt-[11px] flex items-center justify-between gap-6 md:mt-[37px] md:justify-center md:gap-0",
            // `hidden md:flex`, not unmounted: the dash rail is still the
            // desktop's paging indicator, it is only the phone that does
            // without one.
            controls === "md-up" && "hidden md:flex",
          )}
        >
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
 * One of the two paddles: 69×69 beside the track on a desktop, 58×58 under it
 * on a phone. Rendered twice and shown once, because the two positions sit in
 * different parents and faking that with `order` costs more than a second
 * button that is `display: none` half the time.
 *
 * `светлый акцент` at 70% at rest and at full strength under the pointer, as
 * the frame draws the pair — the paddle brightens towards the reader rather
 * than darkening away from them. The night theme keeps solid at rest and
 * `--brand-press` on hover: 70% of the night base over a near-black page is a
 * paddle that half disappears.
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
        "size-[58px] shrink-0 cursor-pointer select-none items-center justify-center self-center rounded-brand bg-brand-control/70 text-brand-mark outline-none transition-[opacity,background-color] duration-[var(--duration-fast)] hover:bg-brand-control focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-brand-control/70 dark:bg-brand-control dark:hover:bg-brand-press dark:disabled:hover:bg-brand-control md:size-[69px]",
        className,
      )}
    >
      {/* 28×42, taller than it is wide — the frame draws the wedge lying down
          and rotates it, so the export's 41×28 is its *pre-rotation* box. Sized
          on both axes for that reason: a square `size-*` would squash it.
          22×30 on a phone, with the paddle itself down to 58. */}
      <Icon className="h-[30px] w-[22px] md:h-[42px] md:w-[28px]" aria-hidden="true" />
    </button>
  );
}
