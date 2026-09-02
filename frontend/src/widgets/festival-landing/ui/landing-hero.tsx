import { CalendarDays, Sparkles } from "lucide-react";
import { formatPeriod, resolveMediaUrl } from "@/features/festival-catalog";
import { type FestivalDetail, heroBlock, landingCta } from "@/features/festival-landing";
import { cn } from "@/shared/lib";
import { Badge } from "@/shared/ui";
import { LandingCtaButton } from "./landing-cta";

interface LandingHeroProps {
  festival: FestivalDetail;
  applyPath: string;
}

/**
 * The large hero header — the public face of the competition.
 *
 * Deliberately almost empty. It carries what the organizer authored on the HERO
 * block (cover, title, subtitle), the dates, and the CTA — and nothing else. The
 * organization's name and the participation formats used to sit here and were
 * removed: a festival's own page is not where its organizer is introduced (that is
 * the footer's job, once), and the formats are a configuration detail that belongs
 * in the summary rail rather than in the first thing a visitor reads.
 *
 * **Nothing is invented.** An unfilled title used to fall back to the competition's
 * own title, which meant the hero always looked authored even when nobody had
 * touched it. It now renders nothing visible — the heading survives for screen
 * readers and search engines, because a page with no ``h1`` is a different kind of
 * broken, but the visitor sees only what the organizer actually wrote.
 *
 * **Two layouts, because one frame cannot hold both.** Text over a photograph needs
 * the photograph cropped to the text's frame, and on a phone that frame is nearly
 * square — so a 1920×600 banner lost everything but a middle strip, which is where a
 * banner keeps the least. From ``sm`` up the block still overlays: the frame is wide,
 * the crop costs the cover little, and the layered hero is the design. Below ``sm``
 * it stacks instead — the banner runs full width at its own proportions, whole, and
 * the badges, title, dates and CTA follow underneath on the page's own background.
 * Same markup, same DOM order, switched by breakpoint rather than by measuring.
 *
 * Status and season are pinned to the top-right corner on the wide layout instead of
 * stacked above the title: they are the two facts a returning visitor scans for, and
 * in the flow they pushed the authored content down the block. Every badge variant is
 * opaque, so they stay legible over a photograph where the scrim has cleared
 * entirely.
 */
export function LandingHero({ festival, applyPath }: LandingHeroProps): React.JSX.Element {
  const hero = heroBlock(festival.landing.blocks);
  const cover = resolveMediaUrl(hero?.coverImage ?? festival.coverImage);
  const title = hero?.title?.trim() || null;
  const subtitle = hero?.subtitle?.trim() || null;
  const cta = landingCta(festival.status);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);

  return (
    <section className="relative isolate overflow-hidden rounded-2xl border">
      {cover ? (
        /* In the flow on a phone, in the backdrop from `sm` up — see the note above. */
        <img
          src={cover}
          alt=""
          className="block w-full sm:absolute sm:inset-0 sm:-z-10 sm:size-full sm:object-cover"
        />
      ) : (
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/25 via-muted to-secondary/25"
        />
      )}
      {/* A scrim, not a curtain. It used to reach 85% of the background colour by
          mid-block and 25% at the very top, which washed the cover out to the point
          that a photograph was barely worth uploading. Now it is opaque only along
          the bottom edge, where the title and the CTA actually sit, and clears
          completely above them — enough contrast for the text, and the picture stays
          a picture.

          Only on the overlaying layout: stacked, the text sits on the page's own
          background and there is nothing to darken for it, so the scrim would be a
          grey film over the bottom of the banner and nothing else. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 hidden bg-gradient-to-t from-background/90 via-background/45 to-transparent sm:block"
      />

      {/* `min-h` only without a cover: with one, the picture gives the block its
          height, and a floor on top of that would open a gap under short copy. */}
      <div
        className={cn(
          "flex flex-col gap-5 p-6 sm:min-h-[28rem] sm:justify-end sm:p-10 sm:pt-20",
          !cover && "min-h-[18rem] justify-end",
        )}
      >
        {/* One node, two placements: pinned out of flow over the cover from `sm` up,
            a plain row above the title when the block is stacked. */}
        <div className="flex flex-wrap gap-2 sm:absolute sm:top-6 sm:right-6 sm:z-10 sm:max-w-[calc(100%-3rem)] sm:justify-end">
          <Badge variant={cta.badgeVariant} size="md" dot>
            {cta.statusLabel}
          </Badge>
          <Badge variant="outline" size="md" icon={<Sparkles className="size-3.5" />}>
            Сезон {festival.season}
          </Badge>
        </div>

        <div className="space-y-3">
          {title ? (
            /* `break-words`: a single long word ("фестиваль-конкурс" at 30px) is
               wider than a 320px screen and the section clips its overflow. */
            <h1 className="text-balance hyphens-auto break-words font-bold text-3xl tracking-tight sm:text-5xl">
              {title}
            </h1>
          ) : (
            <h1 className="sr-only">{festival.title}</h1>
          )}
          {subtitle ? (
            <p className="max-w-3xl text-pretty break-words text-base text-muted-foreground sm:text-lg">
              {subtitle}
            </p>
          ) : null}
        </div>

        {period ? (
          <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <div className="flex items-center gap-2">
              <CalendarDays className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <dt className="sr-only">Даты проведения</dt>
              <dd className="font-medium">{period}</dd>
            </div>
          </dl>
        ) : null}

        <div className="pt-1">
          <LandingCtaButton cta={cta} applyPath={applyPath} />
        </div>
      </div>
    </section>
  );
}
