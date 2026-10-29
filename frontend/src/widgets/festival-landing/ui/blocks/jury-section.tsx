import { resolveMediaUrl } from "@/features/festival-catalog";
import type { JuryCard, LandingBlock } from "@/features/festival-landing";
import { LandingCarousel } from "../landing-carousel";
import { LandingSection } from "../landing-section";

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

/**
 * One jury member: a portrait in its own outlined frame, then the name, the
 * category and whatever the organiser wrote about them.
 *
 * The photo sits in a bordered box inset from the card's own three-pixel
 * outline rather than bleeding to its edges — that inset is what makes the
 * card read as a mounted portrait, and it is the frame's whole gesture here.
 * A near-square box (287×276), because these are head-and-shoulders portraits;
 * the 4:3 landscape the grid used before cropped most of them at the chin.
 */
function JuryMemberCard({ card }: { card: JuryCard }): React.JSX.Element {
  const photo = resolveMediaUrl(card.photo);
  return (
    // 337×481 on a 15px corner with a three-pixel «тёмный акцент» outline, and
    // a floor under the height rather than a fixed one: the frame draws every
    // card the same height whatever is written on it, and a card that is only
    // as tall as its text turns a row of three into a staircase. A longer
    // description grows past the floor instead of being cut.
    // The outline drops to 70% at night: at full strength three of these
    // three-pixel frames over a near-black page read as a cage.
    // 269 wide and centred on a phone, against the page's own 343: the frame
    // insets the card further than the gutter it sits in, the way the catalogue
    // insets its tiles. At the full width it stops reading as a card.
    <article className="mx-auto flex h-full min-h-[382px] w-full max-w-[269px] flex-col gap-1 rounded-brand border-[3px] border-brand-line px-3.5 pt-[18px] pb-3.5 md:min-h-[481px] md:max-w-none md:gap-0 md:px-[25px] md:pt-[21px] md:pb-[25px] dark:border-brand-line/70">
      {/* 287×276 — near-square, because these are head-and-shoulders portraits;
          the 4:3 landscape the grid used before cropped most of them at the
          chin. Its own one-pixel outline, inset from the card's three: that
          inset is what makes the card read as a mounted portrait. */}
      {/* 250×220 on a phone and 287×276 from `md` up — not the same ratio, so
          it is two aspect boxes rather than one scaled down. */}
      <div className="aspect-[250/220] overflow-hidden rounded-brand border border-brand-line bg-background md:aspect-[287/276]">
        {photo ? (
          // Eager, and decoded off the main thread. `loading="lazy"` looks
          // right here and is the reason the first click of the arrow felt
          // heavy: the slides past the right edge of the track are outside the
          // viewport, so nothing beyond the first screen was fetched until the
          // carousel moved — and the decode then landed in the middle of the
          // scroll animation. A jury is a handful of portraits in a fixed box,
          // not an open-ended feed, so loading them with the page is cheaper
          // than paying for it inside the first gesture.
          <img src={photo} alt={card.name} decoding="async" className="size-full object-cover" />
        ) : (
          // Initials rather than an empty plate: the card keeps its silhouette
          // whether or not the organiser uploaded anything.
          <div
            aria-hidden="true"
            className="flex size-full items-center justify-center font-bold text-4xl text-foreground/25"
          >
            {initials(card.name)}
          </div>
        )}
      </div>
      {/* The three lines sit flush on each other — name, category, description —
          with the line height doing all the spacing. The frame leaves no gap
          between them at all, and the block as a whole is what is set apart
          from the portrait above it. */}
      <div>
        <p className="break-words font-bold text-lg leading-[25px] md:text-2xl md:leading-[33px]">
          {card.name}
        </p>
        {card.position ? (
          /* «тёмный акцент» by day and a lit `#B76CD8` by night, through
             `--brand-accent-ink`: the structural violets are drawn to sit under
             light and neither survives as type on a near-black page. One token
             rather than a `dark:` class, because the swap is the theme's
             business and not this card's. */
          <p className="break-words font-bold text-brand-accent-ink text-sm leading-[19px] md:text-base md:leading-[22px]">
            {card.position}
          </p>
        ) : null}
        {card.description ? (
          <p className="text-pretty break-words text-sm leading-[19px] md:text-base md:leading-[22px]">
            {card.description}
          </p>
        ) : null}
      </div>
    </article>
  );
}

interface JurySectionProps {
  block: LandingBlock;
}

/**
 * «Жюри и эксперты» — the jury as a paged carousel rather than a grid.
 *
 * A grid was fine for three and wrong for fifteen: a full-width festival will
 * have a jury longer than the page, and the frame answers that with three
 * cards on screen and paddles either side.
 */
export function JurySection({ block }: JurySectionProps): React.JSX.Element | null {
  if (block.jury.length === 0) {
    return null;
  }
  return (
    <LandingSection
      id={`block-${block.id}`}
      title="Жюри и эксперты"
      align="center"
      headingGap="mb-5 md:mb-[38px]"
    >
      <LandingCarousel
        label="Жюри и эксперты"
        items={block.jury.map((card) => ({
          id: card.id,
          content: <JuryMemberCard card={card} />,
        }))}
        // 19px between cards, so three of them plus two gaps fill the track
        // exactly — the basis has to stay in step with `gapClassName`.
        gapClassName="gap-[19px]"
        sideGapClassName="gap-4 md:gap-[54px]"
        itemClassName="basis-full sm:basis-[calc((100%-1.1875rem)/2)] xl:basis-[calc((100%-2.375rem)/3)]"
      />
    </LandingSection>
  );
}
