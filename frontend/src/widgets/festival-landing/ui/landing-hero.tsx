import { CalendarDays, Clock3, Sparkles } from "lucide-react";
import {
  formatDate,
  formatPeriod,
  participationModeConfig,
  resolveMediaUrl,
} from "@/features/festival-catalog";
import { type FestivalDetail, heroBlock, landingCta } from "@/features/festival-landing";
import { Avatar, Badge } from "@/shared/ui";
import { LandingCtaButton } from "./landing-cta";

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

interface LandingHeroProps {
  festival: FestivalDetail;
  applyPath: string;
}

/**
 * The large hero header — the public face of the competition.
 *
 * Renders the organizer's curated HERO cover/title/subtitle when present, over a
 * gradient that fades into the app background so the overlaid facts stay legible
 * in both themes without hard-coded colors. Everything else (dates, deadline,
 * organization, participation formats, status, CTA) comes from the Competition,
 * the single source of truth.
 */
export function LandingHero({ festival, applyPath }: LandingHeroProps): React.JSX.Element {
  const hero = heroBlock(festival.landing.blocks);
  const cover = resolveMediaUrl(hero?.coverImage ?? festival.coverImage);
  const title = hero?.title?.trim() || festival.title;
  const subtitle = hero?.subtitle?.trim() || null;
  const cta = landingCta(festival.status);

  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);
  const deadline = formatDate(festival.applicationDeadline ?? festival.registrationEnd);
  const logo = resolveMediaUrl(festival.organizer.logo);

  return (
    <section className="relative isolate overflow-hidden rounded-2xl border">
      {cover ? (
        <img src={cover} alt="" className="absolute inset-0 -z-10 size-full object-cover" />
      ) : (
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/25 via-muted to-secondary/25"
        />
      )}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-t from-background via-background/85 to-background/25"
      />

      <div className="flex min-h-[22rem] flex-col justify-end gap-5 p-6 sm:min-h-[28rem] sm:p-10">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={cta.badgeVariant} size="md" dot>
            {cta.statusLabel}
          </Badge>
          <Badge variant="outline" size="md" icon={<Sparkles className="size-3.5" />}>
            Сезон {festival.season}
          </Badge>
        </div>

        <div className="space-y-3">
          {/* `break-words`: a single long word ("фестиваль-конкурс" at 30px) is
              wider than a 320px screen and the section clips its overflow. */}
          <h1 className="text-balance hyphens-auto break-words text-3xl font-bold tracking-tight sm:text-5xl">
            {title}
          </h1>
          {subtitle ? (
            <p className="max-w-3xl text-pretty break-words text-base text-muted-foreground sm:text-lg">
              {subtitle}
            </p>
          ) : null}
        </div>

        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {period ? (
            <div className="flex items-center gap-2">
              <CalendarDays className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <dt className="sr-only">Даты проведения</dt>
              <dd className="font-medium">{period}</dd>
            </div>
          ) : null}
          {deadline ? (
            <div className="flex items-center gap-2">
              <Clock3 className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <dt className="sr-only">Приём заявок до</dt>
              <dd>
                Заявки до <span className="font-medium">{deadline}</span>
              </dd>
            </div>
          ) : null}
        </dl>

        <div className="flex items-center gap-2.5">
          <Avatar
            size="sm"
            {...(logo ? { src: logo } : {})}
            alt={festival.organizer.name}
            fallback={organizerInitials(festival.organizer.name)}
          />
          <span className="text-sm font-medium">{festival.organizer.name}</span>
        </div>

        {festival.formats.length > 0 ? (
          <ul className="flex flex-wrap gap-1.5">
            {festival.formats.map((format) => {
              const config = format.mode ? participationModeConfig(format.mode) : null;
              const Icon = config?.icon;
              return (
                <li key={format.name}>
                  <Badge
                    variant="secondary"
                    size="sm"
                    {...(Icon ? { icon: <Icon className="size-3" /> } : {})}
                  >
                    {format.name}
                  </Badge>
                </li>
              );
            })}
          </ul>
        ) : null}

        <div className="pt-1">
          <LandingCtaButton cta={cta} applyPath={applyPath} />
        </div>
      </div>
    </section>
  );
}
