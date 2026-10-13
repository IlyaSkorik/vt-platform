import { resolveMediaUrl } from "@/features/festival-catalog";
import { type FestivalDetail, heroBlock } from "@/features/festival-landing";
import { PosterImage } from "@/shared/ui";

interface LandingCoverProps {
  festival: FestivalDetail;
}

/**
 * The festival's banner — the first thing on the page, and now the only thing
 * in that band.
 *
 * It used to be a hero: the cover was a backdrop with a scrim over it and the
 * title, the dates, the status badges and the CTA laid on top. The frame takes
 * all of that out and moves it into the card below, leaving the artwork to be
 * artwork. That is the right call for what organisers actually upload — these
 * are designed posters that already carry the festival's name, its dates and
 * its city, so the overlay was printing every one of them twice.
 *
 * Shown whole rather than cropped (`PosterImage` fits and fills the sides with
 * a blurred copy of itself): a poster keeps its title at the top and its dates
 * at the bottom, which is exactly what a 1293×343 crop takes away.
 *
 * The cover comes off the HERO block when the organiser set one there and off
 * the festival otherwise — the same precedence the overlay hero used, so
 * nobody's uploaded banner changes which image wins.
 */
export function LandingCover({ festival }: LandingCoverProps): React.JSX.Element | null {
  const hero = heroBlock(festival.landing.blocks);
  const cover = resolveMediaUrl(hero?.coverImage ?? festival.coverImage);
  if (!cover) {
    return null;
  }
  return (
    // 343px on the desktop and 189 on a phone, as the frame measures them, and
    // a fixed height rather than an aspect ratio: the band is a slot the page
    // reserves, and posters arrive at every proportion there is.
    <div className="h-[189px] overflow-hidden rounded-brand bg-muted md:h-[343px]">
      <PosterImage src={cover} alt={`Афиша фестиваля «${festival.title}»`} loading="eager" />
    </div>
  );
}
