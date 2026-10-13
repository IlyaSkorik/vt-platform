import { ExternalLink } from "lucide-react";
import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock, PartnerCard } from "@/features/festival-landing";
import { Button } from "@/shared/ui";
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
    <article className="flex w-[220px] flex-col items-center gap-3 rounded-brand border border-brand-line px-4 py-5">
      <div className="flex size-[127px] shrink-0 items-center justify-center overflow-hidden rounded-full bg-foreground/40">
        {logo ? (
          <img src={logo} alt={partner.name} className="size-full object-contain" />
        ) : (
          <span aria-hidden="true" className="text-foreground text-xl leading-[27px]">
            ЛОГО
          </span>
        )}
      </div>
      <p className="break-words text-center text-base leading-[22px] md:text-xl md:leading-[27px]">
        {partner.name}
      </p>
      {partner.website ? (
        <Button
          asChild
          variant="outline"
          className="h-[30px] rounded-[10px] border-brand-line bg-background font-heading font-normal text-foreground text-sm leading-[19px] shadow-none"
        >
          <a href={partner.website} target="_blank" rel="noopener noreferrer">
            Сайт
            <ExternalLink className="size-4" aria-hidden="true" />
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
    <LandingSection id={`block-${block.id}`} title="Партнеры" align="center">
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
