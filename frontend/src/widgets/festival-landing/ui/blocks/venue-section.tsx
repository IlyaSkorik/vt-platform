import { ExternalLink, Map as MapIcon, MapPin, Navigation } from "lucide-react";
import type { FestivalVenue } from "@/features/festival-landing";
import { Button, Card, CardContent } from "@/shared/ui";
import { LandingSection } from "../landing-section";

/** True when the venue carries anything worth rendering. */
export function hasVenueContent(venue: FestivalVenue): boolean {
  return Boolean(
    venue.name ||
      venue.address ||
      venue.city ||
      venue.country ||
      venue.directions ||
      venue.googleMapsUrl ||
      venue.yandexMapsUrl,
  );
}

interface VenueSectionProps {
  id: string;
  venue: FestivalVenue;
}

/**
 * The VENUE block: place, address and directions.
 *
 * Reuses Competition Contacts verbatim — the organizer configures the venue once
 * and it is the single source of truth; this section never duplicates it.
 */
export function VenueSection({ id, venue }: VenueSectionProps): React.JSX.Element | null {
  if (!hasVenueContent(venue)) {
    return null;
  }
  const locality = [venue.city, venue.country].filter(Boolean).join(", ");
  return (
    <LandingSection id={id} title="Место проведения">
      <Card>
        <CardContent className="space-y-4 pt-6">
          <div className="flex items-start gap-3">
            <MapPin className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
            <div className="space-y-0.5">
              {venue.name ? <p className="font-semibold">{venue.name}</p> : null}
              {venue.address ? <p className="text-muted-foreground">{venue.address}</p> : null}
              {locality ? <p className="text-sm text-muted-foreground">{locality}</p> : null}
            </div>
          </div>

          {venue.directions ? (
            <div className="flex items-start gap-3">
              <Navigation
                className="mt-0.5 size-5 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <p className="whitespace-pre-line text-pretty text-sm leading-relaxed text-muted-foreground">
                {venue.directions}
              </p>
            </div>
          ) : null}

          {venue.googleMapsUrl || venue.yandexMapsUrl ? (
            <div className="flex flex-wrap gap-2 pt-1">
              {venue.googleMapsUrl ? (
                <Button asChild variant="outline" size="sm">
                  <a href={venue.googleMapsUrl} target="_blank" rel="noopener noreferrer">
                    <MapIcon className="size-4" aria-hidden="true" />
                    Google Карты
                    <ExternalLink className="size-3" aria-hidden="true" />
                  </a>
                </Button>
              ) : null}
              {venue.yandexMapsUrl ? (
                <Button asChild variant="outline" size="sm">
                  <a href={venue.yandexMapsUrl} target="_blank" rel="noopener noreferrer">
                    <MapIcon className="size-4" aria-hidden="true" />
                    Яндекс Карты
                    <ExternalLink className="size-3" aria-hidden="true" />
                  </a>
                </Button>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </LandingSection>
  );
}
