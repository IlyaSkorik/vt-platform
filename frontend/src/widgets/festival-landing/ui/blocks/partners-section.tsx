import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock, PartnerCard } from "@/features/festival-landing";
import { Button, OpenInNewIcon } from "@/shared/ui";
import { LandingSection } from "../landing-section";

/**
 * One partner: the logo in a circle, the name under it, and — only when the
 * organiser gave one — a link out to their site.
 *
 * The whole tile used to be the link. It is a button now because the frame
 * draws one, and because a tile that is entirely clickable has no way to show
 * a partner who has no website: the markup silently changed shape, and two
 * tiles side by side behaved differently with nothing to say so.
 */
function PartnerTile({ partner }: { partner: PartnerCard }): React.JSX.Element {
  const logo = resolveMediaUrl(partner.logo);
  return (
    // 220×233 on a one-pixel outline, with a floor under the height rather than
    // a fixed one so a two-line partner name grows the tile instead of spilling
    // out of it.
    //
    // «Акцент темный» by day and «светлый база ночная» by night: the saturated
    // violet is a line you can see against «свет» and a line that vanishes
    // against `#110B12`, so after dark the frame outlines these in the greyed
    // violet it gives every night control.
    <article className="flex min-h-[233px] w-[220px] flex-col items-center rounded-brand border border-brand-line-vivid px-3 pt-[19px] pb-[11px] dark:border-brand-control">
      {/* The disc is 40% of «Темный текст» on a pale page and 70% of «свет» on
          a dark one — a light shape either way, which is why the stand-in label
          on it takes the page's own colour after dark. The frame prints that
          label in «свет» there, which would be white on a near-white disc. */}
      <div className="flex size-[127px] shrink-0 items-center justify-center overflow-hidden rounded-full bg-foreground/40 dark:bg-foreground/70">
        {logo ? (
          <img
            src={logo}
            alt={partner.name}
            decoding="async"
            className="size-full object-contain"
          />
        ) : (
          <span aria-hidden="true" className="text-xl leading-[27px] dark:text-background">
            ЛОГО
          </span>
        )}
      </div>
      <p className="mt-2 break-words text-center text-base leading-[22px] md:text-xl md:leading-[27px]">
        {partner.name}
      </p>
      {partner.website ? (
        // 103×33 on a 10px corner — the same corner the map links wear, and the
        // same arrangement: the label against the left edge, the open-in-new
        // mark against the right.
        //
        // «Акцент темный» in *both* themes, unlike the tile around it: the tile
        // is a large shape and the saturated violet reads as a cage around it
        // after dark, which is why that one drops to «светлый база ночная». A
        // 103px control is small enough to keep the brand colour, and keeping
        // it is what separates the button from the outline it sits inside.
        <Button
          asChild
          variant="outline"
          className="mt-2 h-[33px] w-[103px] justify-between rounded-[10px] border-brand-line-vivid bg-background px-4 font-heading font-normal text-base text-foreground leading-[22px] shadow-none md:text-lg md:leading-[25px]"
        >
          <a href={partner.website} target="_blank" rel="noopener noreferrer">
            Сайт
            <OpenInNewIcon className="size-[14.25px]" aria-hidden="true" />
          </a>
        </Button>
      ) : null}
    </article>
  );
}

interface PartnersSectionProps {
  block: LandingBlock;
}

/** «Партнеры» — a centred row of partner tiles that wraps rather than scrolls:
 * there are rarely more than a handful, and a carousel for four logos is
 * machinery nobody needs. */
export function PartnersSection({ block }: PartnersSectionProps): React.JSX.Element | null {
  if (block.partners.length === 0) {
    return null;
  }
  return (
    <LandingSection
      id={`block-${block.id}`}
      title="Партнеры"
      align="center"
      headingGap="mb-5 md:mb-[26px]"
    >
      <ul className="flex flex-wrap justify-center gap-[26px]">
        {block.partners.map((partner) => (
          <li key={partner.id}>
            <PartnerTile partner={partner} />
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
