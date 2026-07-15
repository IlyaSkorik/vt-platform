import { ArrowRight, CalendarDays, Clock3, MapPin, Ticket } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import {
  catalogStatusConfig,
  type Festival,
  formatDeadline,
  formatPeriod,
  formatPrice,
  isClosingSoon,
  participationModeConfig,
  resolveMediaUrl,
} from "@/features/festival-catalog";
import { ROUTES } from "@/shared/config";
import { Avatar, Badge, Button, Card, CardContent, CardFooter } from "@/shared/ui";

interface FestivalCardProps {
  festival: Festival;
  now: Date;
  detailBasePath?: string;
}

function organizerInitials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

/** A single competition tile — the atom of the catalog grid. */
export function FestivalCard({
  festival,
  now,
  detailBasePath = ROUTES.cabinetCompetitions,
}: FestivalCardProps): React.JSX.Element {
  const { isAuthenticated } = useAuth();
  const status = catalogStatusConfig(festival.status);
  const cover = resolveMediaUrl(festival.coverImage);
  const price = formatPrice(festival);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);
  const deadline = formatDeadline(festival);
  const closingSoon = isClosingSoon(festival, now);
  const logo = resolveMediaUrl(festival.organizer.logo);

  const detailPath = `${detailBasePath}/${festival.id}`;
  const cabinetApplyPath = `${ROUTES.cabinetCompetitions}/${festival.id}/apply`;
  const applyPath = isAuthenticated
    ? cabinetApplyPath
    : `${ROUTES.login}?next=${encodeURIComponent(cabinetApplyPath)}`;

  return (
    <Card className="group flex h-full flex-col overflow-hidden transition-shadow hover:shadow-md">
      <Link
        to={detailPath}
        aria-label={`Подробнее: ${festival.title}`}
        className="relative block aspect-[16/10] overflow-hidden bg-muted outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {cover ? (
          <img
            src={cover}
            alt=""
            loading="lazy"
            className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div
            aria-hidden="true"
            className="flex size-full items-center justify-center bg-gradient-to-br from-primary/15 via-muted to-secondary/15"
          >
            <Ticket className="size-10 text-muted-foreground/60" />
          </div>
        )}

        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-3">
          <div className="flex min-w-0 flex-wrap gap-1.5">
            <Badge variant={status.badgeVariant} size="sm">
              {status.label}
            </Badge>
            {closingSoon ? (
              <Badge variant="danger" size="sm" dot>
                Скоро закрытие
              </Badge>
            ) : null}
          </div>
          {price ? (
            <span className="shrink-0 whitespace-nowrap rounded-full bg-background/90 px-2.5 py-1 text-xs font-semibold text-foreground shadow-sm backdrop-blur">
              {price}
            </span>
          ) : null}
        </div>
      </Link>

      <CardContent className="flex flex-1 flex-col gap-3 pt-5">
        <div className="space-y-1">
          <h3 className="line-clamp-2 text-base font-semibold leading-snug">
            <Link
              to={detailPath}
              className="outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
            >
              {festival.title}
            </Link>
          </h3>
          <p className="truncate text-sm text-muted-foreground">{festival.organizer.name}</p>
        </div>

        <dl className="grid gap-1.5 text-sm text-muted-foreground">
          {festival.city ? (
            <div className="flex items-center gap-2">
              <MapPin className="size-4 shrink-0" aria-hidden="true" />
              <dd className="truncate">{festival.city}</dd>
            </div>
          ) : null}
          {period ? (
            <div className="flex items-center gap-2">
              <CalendarDays className="size-4 shrink-0" aria-hidden="true" />
              <dd className="truncate">{period}</dd>
            </div>
          ) : null}
          {deadline && status.apply.visible ? (
            <div className="flex items-center gap-2">
              <Clock3 className="size-4 shrink-0" aria-hidden="true" />
              <dd className="truncate">
                Заявки до <span className="text-foreground">{deadline}</span>
              </dd>
            </div>
          ) : null}
        </dl>

        {festival.modes.length > 0 ? (
          <ul className="mt-auto flex flex-wrap gap-1.5 pt-1">
            {festival.modes.map((mode) => {
              const config = participationModeConfig(mode);
              if (!config) {
                return null;
              }
              const Icon = config.icon;
              return (
                <li key={mode}>
                  <Badge variant="outline" size="sm" icon={<Icon className="size-3" />}>
                    {config.label}
                  </Badge>
                </li>
              );
            })}
          </ul>
        ) : null}
      </CardContent>

      <CardFooter className="mt-auto flex-col items-stretch gap-3 border-t pt-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Avatar
            size="xs"
            {...(logo ? { src: logo } : {})}
            alt={festival.organizer.name}
            fallback={organizerInitials(festival.organizer.name)}
          />
          <span className="truncate">Сезон {festival.season}</span>
        </div>
        <div className="grid gap-2">
          {status.apply.visible ? (
            status.apply.enabled ? (
              <Button asChild size="sm">
                <Link to={applyPath}>
                  {status.apply.label}
                  <ArrowRight className="size-3.5" aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <Button size="sm" disabled>
                {status.apply.label}
              </Button>
            )
          ) : null}
          <Button asChild variant={status.apply.visible ? "outline" : "primary"} size="sm">
            <Link to={detailPath}>Подробнее</Link>
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
