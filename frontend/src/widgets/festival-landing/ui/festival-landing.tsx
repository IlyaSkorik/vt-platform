import { ArrowLeft } from "lucide-react";
import { Link } from "react-router";
import { type FestivalDetail, usePublicFestival } from "@/features/festival-landing";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";
import { LandingFooter } from "./landing-footer";
import { LandingHero } from "./landing-hero";
import { LandingSections } from "./landing-sections";
import { LandingSkeleton } from "./landing-skeleton";
import { LandingError, LandingNotFound } from "./landing-states";
import { LandingSummary } from "./landing-summary";
import { RegulationSection } from "./regulation-section";

interface FestivalLandingProps {
  festivalId: string | undefined;
}

function BackLink(): React.JSX.Element {
  return (
    <Button asChild variant="ghost" size="sm" leftIcon={<ArrowLeft aria-hidden="true" />}>
      <Link to={ROUTES.cabinetCompetitions}>К каталогу</Link>
    </Button>
  );
}

function LandingContent({ festival }: { festival: FestivalDetail }): React.JSX.Element {
  const applyPath = `${ROUTES.cabinetCompetitions}/${festival.id}/apply`;
  return (
    <div className="space-y-10">
      <LandingHero festival={festival} applyPath={applyPath} />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        {/* Summary sits after the hero on mobile/tablet and becomes the sticky
            right rail on desktop (order swap keeps a single DOM source). */}
        <aside className="lg:sticky lg:top-6 lg:order-2 lg:self-start">
          <LandingSummary festival={festival} applyPath={applyPath} />
        </aside>
        <main className="min-w-0 space-y-14 lg:order-1">
          {festival.regulation ? <RegulationSection regulation={festival.regulation} /> : null}
          <LandingSections festival={festival} />
        </main>
      </div>
      <LandingFooter contacts={festival.contacts} />
    </div>
  );
}

/**
 * The public Competition Landing Page.
 *
 * Owns data (a single cached read of the public detail projection) and every UI
 * state: skeleton while loading, a dedicated not-found for a missing/unpublished
 * competition (404), a retryable error otherwise, and the full landing on
 * success. It composes the hero, the organizer's Landing Builder blocks, the
 * sticky summary and the reused Competition Contacts footer.
 */
export function FestivalLanding({ festivalId }: FestivalLandingProps): React.JSX.Element {
  const query = usePublicFestival(festivalId);

  if (!festivalId) {
    return (
      <div className="space-y-6">
        <BackLink />
        <LandingNotFound />
      </div>
    );
  }

  if (query.isPending) {
    return <LandingSkeleton />;
  }

  if (query.isError) {
    if (query.error.status === 404) {
      return (
        <div className="space-y-6">
          <BackLink />
          <LandingNotFound />
        </div>
      );
    }
    return (
      <div className="space-y-6">
        <BackLink />
        <LandingError onRetry={() => void query.refetch()} retrying={query.isFetching} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BackLink />
      <LandingContent festival={query.data} />
    </div>
  );
}
