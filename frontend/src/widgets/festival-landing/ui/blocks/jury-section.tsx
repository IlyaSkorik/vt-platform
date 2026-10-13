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
    <article className="flex h-full flex-col gap-3 rounded-brand border-[3px] border-brand-line p-4 md:gap-4 md:p-[25px]">
      <div className="aspect-[287/276] overflow-hidden rounded-brand border border-brand-line bg-background">
        {photo ? (
          <img src={photo} alt={card.name} loading="lazy" className="size-full object-cover" />
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
      <div className="space-y-0.5">
        <p className="break-words font-bold text-lg leading-[25px] md:text-2xl md:leading-[33px]">
          {card.name}
        </p>
        {card.position ? (
          <p className="break-words font-bold text-brand-line text-sm leading-[19px] md:text-base md:leading-[22px]">
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
    <LandingSection id={`block-${block.id}`} title="Жюри и эксперты" align="center">
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
