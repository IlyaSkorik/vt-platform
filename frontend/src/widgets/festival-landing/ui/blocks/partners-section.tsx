import { ExternalLink } from "lucide-react";
import { resolveMediaUrl } from "@/features/festival-catalog";
import type { LandingBlock, PartnerCard } from "@/features/festival-landing";
import { Card } from "@/shared/ui";
import { LandingSection } from "../landing-section";

function PartnerTile({ partner }: { partner: PartnerCard }): React.JSX.Element {
  const logo = resolveMediaUrl(partner.logo);
  const body = (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-5 text-center">
      {logo ? (
        <img src={logo} alt={partner.name} className="h-12 max-w-full object-contain" />
      ) : (
        <span className="text-sm font-semibold">{partner.name}</span>
      )}
      {logo ? <span className="text-xs text-muted-foreground">{partner.name}</span> : null}
      {partner.website ? (
        <span className="inline-flex items-center gap-1 text-xs text-primary">
          Сайт
          <ExternalLink className="size-3" aria-hidden="true" />
        </span>
      ) : null}
    </div>
  );

  if (partner.website) {
    return (
      <Card className="h-full transition-shadow hover:shadow-md">
        <a
          href={partner.website}
          target="_blank"
          rel="noopener noreferrer"
          className="block h-full rounded-[inherit] outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {body}
        </a>
      </Card>
    );
  }
  return <Card className="h-full">{body}</Card>;
}

interface PartnersSectionProps {
  block: LandingBlock;
}

/** The PARTNERS block: a grid of partner/sponsor tiles. */
export function PartnersSection({ block }: PartnersSectionProps): React.JSX.Element | null {
  if (block.partners.length === 0) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title="Партнёры">
      <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {block.partners.map((partner) => (
          <li key={partner.id}>
            <PartnerTile partner={partner} />
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
