import { resolveMediaUrl } from "@/features/festival-catalog";
import type { JuryCard, LandingBlock } from "@/features/festival-landing";
import { Card, CardContent } from "@/shared/ui";
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

function JuryMemberCard({ card }: { card: JuryCard }): React.JSX.Element {
  const photo = resolveMediaUrl(card.photo);
  return (
    <Card className="h-full overflow-hidden">
      {/* Full-width portrait on top; a gradient + initials fill in when the
          organizer left no photo, so every card keeps the same silhouette. */}
      <div className="aspect-[4/3] bg-muted">
        {photo ? (
          <img src={photo} alt={card.name} loading="lazy" className="size-full object-cover" />
        ) : (
          <div
            aria-hidden="true"
            className="flex size-full items-center justify-center bg-gradient-to-br from-primary/20 via-muted to-secondary/20"
          >
            <span className="text-3xl font-semibold text-muted-foreground">
              {initials(card.name)}
            </span>
          </div>
        )}
      </div>
      <CardContent className="space-y-1.5 pt-4">
        <p className="font-semibold leading-snug">{card.name}</p>
        {card.position ? <p className="text-sm font-medium text-primary">{card.position}</p> : null}
        {card.description ? (
          <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
            {card.description}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

interface JurySectionProps {
  block: LandingBlock;
}

/** The JURY block: a grid of jury/expert cards — photo on top, then name,
 * position and a free-length description. */
export function JurySection({ block }: JurySectionProps): React.JSX.Element | null {
  if (block.jury.length === 0) {
    return null;
  }
  return (
    <LandingSection id={`block-${block.id}`} title="Жюри и эксперты">
      <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {block.jury.map((card) => (
          <li key={card.id}>
            <JuryMemberCard card={card} />
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
