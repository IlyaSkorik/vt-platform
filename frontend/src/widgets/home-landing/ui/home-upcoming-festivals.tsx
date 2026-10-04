import { Link } from "react-router";
import type { Festival } from "@/features/festival-catalog";
import { Button, EmptyState, LoadingState } from "@/shared/ui";
import { HomeFestivalCarousel } from "./home-festival-carousel";

interface HomeUpcomingFestivalsProps {
  festivals: readonly Festival[];
  isPending: boolean;
  /** Where «Все фестивали» leads. */
  allFestivalsPath: string;
  hrefFor: (festival: Festival) => string;
}

/**
 * The «Ближайшие фестивали» band: heading, the carousel, and the way out to the
 * full catalog.
 *
 * The section owns the three states the carousel itself should not have to know
 * about — loading, nothing to show, and something to show. Giving the carousel
 * an empty array would leave it rendering a pair of disabled paddles around a
 * void, which looks like a failure rather than like "no festivals are announced
 * yet"; and the «Все фестивали» button is kept out of the empty branch's bottom
 * because the empty state already carries it as the one thing worth doing.
 *
 * The anchor id is what the hero's first button jumps to, so it is part of this
 * component's contract rather than an incidental hook.
 */
export function HomeUpcomingFestivals({
  festivals,
  isPending,
  allFestivalsPath,
  hrefFor,
}: HomeUpcomingFestivalsProps): React.JSX.Element {
  return (
    <section id="upcoming-festivals" className="scroll-mt-24">
      {/* Indented to the first card, not to the page gutter. The carousel puts
          a 70px paddle and a 1.5rem gap to the left of its track, so the cards
          start that far in and a heading flush with the container reads as
          hanging off the row it titles. Below `md` the paddles are not rendered
          and the cards do start at the gutter, so the offset goes with them.

          The one coupling worth naming: if `CarouselArrow` changes size, or the
          row's `md:gap-6` moves, this number has to follow. */}
      <h2 className="font-heading font-bold text-2xl text-foreground leading-snug tracking-tight md:ml-[calc(70px+1.5rem)] md:text-[1.75rem]">
        Ближайшие фестивали
      </h2>

      {isPending ? (
        <LoadingState label="Загружаем ближайшие фестивали…" className="mt-8 py-16" />
      ) : festivals.length === 0 ? (
        <EmptyState
          className="mt-8"
          title="Фестивали пока не объявлены"
          description="Как только организаторы откроют регистрацию, мероприятия появятся здесь."
          action={
            <Button
              asChild
              size="lg"
              className="rounded-brand px-7 font-heading font-bold hover:bg-brand-line dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
            >
              <Link to={allFestivalsPath}>Все фестивали</Link>
            </Button>
          }
        />
      ) : (
        <>
          {/* `animate-rise-in` on the band rather than on each tile: the list
              arrives as one thing when the query resolves, and staggering it
              would draw attention to the loading instead of away from it. */}
          <div className="mt-8 animate-rise-in">
            <HomeFestivalCarousel festivals={festivals} hrefFor={hrefFor} />
          </div>
          {/* 60px below the dots, which already sit 80px below the cards —
              both measured off the frame. */}
          <div className="mt-15 flex justify-center">
            {/* 225×43 on the landing's 15px corner, label in Noto Serif Bold
                24/33 — `leading-snug` lands on 33px exactly at this size. The
                type is a step up from the 18px the hero's buttons carry, which
                is what makes this the page's one «and now the whole catalogue»
                control rather than a third button of the same weight; the plate
                is the same 43px tall as the hero's, so the two still read as the
                same family. */}
            <Button
              asChild
              size="lg"
              className="h-[43px] w-[225px] rounded-brand px-0 font-heading font-bold text-2xl leading-snug hover:bg-brand-line dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
            >
              <Link to={allFestivalsPath}>Все фестивали</Link>
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
