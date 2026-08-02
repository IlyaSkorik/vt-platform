import { ArrowUpRight, CalendarDays, Sparkles, TrendingUp } from "lucide-react";
import { Link } from "react-router";
import {
  catalogStatusConfig,
  type Festival,
  formatPeriod,
  resolveMediaUrl,
  selectFeatured,
  selectUpcoming,
} from "@/features/festival-catalog";
import { ROUTES } from "@/shared/config";
import { festivalPath } from "@/shared/lib";
import { Badge, Card, CardContent } from "@/shared/ui";

function cabinetPath(festival: Festival): string {
  return festivalPath(festival, ROUTES.cabinetCompetitions);
}

function FeaturedFestival({ festival }: { festival: Festival }): React.JSX.Element {
  const cover = resolveMediaUrl(festival.coverImage);
  const status = catalogStatusConfig(festival.status);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);
  return (
    <Card className="overflow-hidden">
      <Link
        to={cabinetPath(festival)}
        className="block outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="relative aspect-[16/10] bg-muted">
          {cover ? (
            <img src={cover} alt="" loading="lazy" className="size-full object-cover" />
          ) : (
            <div
              aria-hidden="true"
              className="flex size-full items-center justify-center bg-gradient-to-br from-primary/15 via-muted to-secondary/15"
            >
              <Sparkles className="size-8 text-muted-foreground/60" />
            </div>
          )}
          <div className="absolute left-3 top-3">
            <Badge variant={status.badgeVariant} size="sm">
              {status.label}
            </Badge>
          </div>
        </div>
        <CardContent className="space-y-1 pt-4">
          <p className="line-clamp-2 font-semibold leading-snug">{festival.title}</p>
          <p className="truncate text-sm text-muted-foreground">{festival.organizer.name}</p>
          {period ? (
            <p className="flex items-center gap-1.5 pt-1 text-sm text-muted-foreground">
              <CalendarDays className="size-4 shrink-0" aria-hidden="true" />
              {period}
            </p>
          ) : null}
        </CardContent>
      </Link>
    </Card>
  );
}

function UpcomingRow({ festival }: { festival: Festival }): React.JSX.Element {
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);
  return (
    <Link
      to={cabinetPath(festival)}
      className="group flex items-center gap-3 rounded-md p-2 outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{festival.title}</p>
        {period ? <p className="truncate text-xs text-muted-foreground">{period}</p> : null}
      </div>
      <ArrowUpRight
        className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
        aria-hidden="true"
      />
    </Link>
  );
}

interface FestivalFeaturedPanelProps {
  festivals: Festival[];
}

/**
 * Right-hand showcase: one headlined festival plus an "upcoming" shortlist.
 * Hidden on small screens by the parent layout.
 */
export function FestivalFeaturedPanel({
  festivals,
}: FestivalFeaturedPanelProps): React.JSX.Element | null {
  const featured = selectFeatured(festivals);
  if (!featured) {
    return null;
  }
  const upcoming = selectUpcoming(festivals, featured.id, 4);

  return (
    <div className="space-y-5">
      <section aria-labelledby="featured-heading" className="space-y-3">
        <h2 id="featured-heading" className="flex items-center gap-2 text-sm font-semibold">
          <Sparkles className="size-4 text-primary" aria-hidden="true" />
          Рекомендуем
        </h2>
        <FeaturedFestival festival={featured} />
      </section>

      {upcoming.length > 0 ? (
        <section aria-labelledby="upcoming-heading" className="space-y-2">
          <h2 id="upcoming-heading" className="flex items-center gap-2 text-sm font-semibold">
            <TrendingUp className="size-4 text-primary" aria-hidden="true" />
            Скоро
          </h2>
          <Card>
            <CardContent className="flex flex-col gap-1 py-3">
              {upcoming.map((festival) => (
                <UpcomingRow key={festival.id} festival={festival} />
              ))}
            </CardContent>
          </Card>
        </section>
      ) : null}
    </div>
  );
}
