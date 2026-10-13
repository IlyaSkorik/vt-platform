import { Navigation } from "lucide-react";
import type { FestivalVenue } from "@/features/festival-landing";
import { LandingSection } from "../landing-section";

interface VenueSectionProps {
  id: string;
  venue: FestivalVenue;
}

/**
 * The VENUE block — now only «Как добраться», the organiser's directions.
 *
 * The place itself moved into the summary card at the top of the page, where
 * the frame puts it: the name, the locality and the two map links are the
 * first things a visitor looks for, and they were a scroll away down the
 * column. What the card has no room for is a paragraph of directions, so that
 * is what this block kept — rendered only when the organiser wrote one, which
 * also means enabling the block no longer prints an address the page has
 * already given above.
 */
export function VenueSection({ id, venue }: VenueSectionProps): React.JSX.Element | null {
  const directions = venue.directions?.trim();
  if (!directions) {
    return null;
  }
  return (
    <LandingSection id={id} title="Как добраться">
      <div className="flex items-start gap-3 rounded-[19px] border border-brand-line px-3 py-3 md:px-3.5">
        <Navigation className="mt-1 size-5 shrink-0 md:size-6" aria-hidden="true" />
        <p className="min-w-0 whitespace-pre-line break-words text-pretty text-sm leading-[19px] md:text-lg md:leading-[25px]">
          {directions}
        </p>
      </div>
    </LandingSection>
  );
}
