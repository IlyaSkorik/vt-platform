import { formatPeriod } from "@/features/festival-catalog";
import {
  type FestivalDetail,
  type FestivalVenue,
  heroBlock,
  landingCta,
} from "@/features/festival-landing";
import { Button, CalendarIcon, MapIcon, MapPinIcon, OpenInNewIcon } from "@/shared/ui";
import { LandingCtaButton } from "./landing-cta";

interface SummaryRowProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
}

/**
 * One labelled fact: the icon and the label on the first line, the value under
 * them and indented to the label's left edge — the frame's own arrangement, and
 * the reason the value is not beside the icon. It gives a two-line address the
 * full width of the card instead of a column 40px narrower.
 */
function SummaryRow({ icon: Icon, label, children }: SummaryRowProps): React.JSX.Element {
  return (
    <div>
      {/* 59% of «Темный текст» by day, 70% of «свет» by night — the frame's own
          two numbers. The icon takes the label's colour, as it does there. */}
      <dt className="flex items-center gap-4 text-foreground/60 dark:text-foreground/70">
        <Icon className="size-5 shrink-0 md:size-6" aria-hidden="true" />
        <span className="uppercase text-sm leading-[19px] md:text-lg md:leading-[25px]">
          {label}
        </span>
      </dt>
      {/* `pl-9`/`pl-10` is the icon's own width plus the gap, so the value lines
          up under the label rather than under the icon. */}
      <dd className="pl-9 text-foreground text-sm leading-[19px] md:pl-10 md:text-lg md:leading-[25px]">
        {children}
      </dd>
    </div>
  );
}

/** The address as the frame prints it: locality on one line, the venue on the next. */
function venueLines(venue: FestivalVenue, fallbackCity: string | null): string[] {
  const locality = [venue.country, venue.city ?? fallbackCity].filter(Boolean).join(", ");
  return [locality, venue.name, venue.address].filter((line): line is string => Boolean(line));
}

interface MapLinkProps {
  href: string;
  children: React.ReactNode;
}

/**
 * One of the two map links: an outlined 197×39 plate on a 10px corner — the one
 * radius on the page that is *not* the brand's 15, which is why it is written
 * out rather than taken from `rounded-brand`.
 *
 * `justify-between`, so the map mark sits against the left edge and the
 * open-in-new mark against the right with the label between them, whichever of
 * the two services it names: «Google Карты» and «Яндекс Карты» differ by a
 * character and the pair would otherwise be visibly off from each other.
 */
function MapLink({ href, children }: MapLinkProps): React.JSX.Element {
  return (
    <Button
      asChild
      variant="outline"
      className="h-[34px] w-[165px] justify-between rounded-[10px] border-brand-line bg-background px-2.5 font-heading font-normal text-foreground text-sm leading-[19px] shadow-none md:h-[39px] md:w-[197px] md:text-base md:leading-[22px]"
    >
      <a href={href} target="_blank" rel="noopener noreferrer">
        {/* 18 and 14.25 — the glyphs' own sizes in the export, not the frames
            they were cropped from, and the same on a phone: shrinking them with
            the plate left the map mark illegible at 15px. */}
        <MapIcon className="size-[18px]" aria-hidden="true" />
        {children}
        <OpenInNewIcon className="size-[14.25px]" aria-hidden="true" />
      </a>
    </Button>
  );
}

interface LandingSummaryProps {
  festival: FestivalDetail;
  applyPath: string;
}

/**
 * The festival's card — the left-hand column of the page, and the page's `h1`.
 *
 * This is where the overlay hero's contents went. The title, the dates and the
 * place now sit in a bordered panel beside the registration column instead of
 * over the poster, and the CTA is the plate directly under it: a reader who
 * scrolls past the banner keeps the festival's name, its dates, its venue and
 * the way in all in one frame.
 *
 * **Two rows and no more: the dates and the place.** The price and the
 * participation formats were tried here and taken out again — the card is the
 * page's one glance, and a list that keeps growing stops being one. Both are
 * still asked and answered inside the application wizard, which is where a
 * visitor meets them at the moment they matter.
 *
 * The title prefers what the organiser wrote on the HERO block and falls back
 * to the festival's own — the same precedence the hero used, so nobody's
 * authored title disappears now that the overlay is gone.
 */
export function LandingSummary({ festival, applyPath }: LandingSummaryProps): React.JSX.Element {
  const hero = heroBlock(festival.landing.blocks);
  const title = hero?.title?.trim() || festival.title;
  const cta = landingCta(festival.status);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);
  const { venue } = festival.contacts;
  const lines = venueLines(venue, festival.city);
  const maps = venue.googleMapsUrl || venue.yandexMapsUrl;

  return (
    <div className="flex flex-col gap-6 md:gap-2.5">
      {/* `bg-background`, not `bg-card`: the frame fills the panel with `свет`
          — the page's own colour — and lets the two-pixel «тёмный акцент»
          outline be the whole of what separates it from the page. */}
      {/* One pixel of outline on a phone and two on a desktop: the card is
          nearly the whole screen there, and a two-pixel frame around it reads
          as a box drawn round the page rather than as a panel on it. */}
      <div className="rounded-brand border border-brand-line bg-background px-4 pt-3 pb-5 md:border-2 md:px-5 md:pb-6">
        <h1 className="text-balance text-center font-bold text-lg leading-[25px] md:text-[28px] md:leading-[38px]">
          {title}
        </h1>
        <p className="text-center text-base leading-[22px] md:text-lg md:leading-[25px]">
          Кратко о фестивале
        </p>

        <dl className="mt-5 space-y-3 md:mt-6 md:space-y-4">
          {period ? (
            <SummaryRow icon={CalendarIcon} label="Даты проведения">
              {period}
            </SummaryRow>
          ) : null}
          {lines.length > 0 ? (
            <SummaryRow icon={MapPinIcon} label="Место проведения">
              {lines.map((line) => (
                <span key={line} className="block break-words">
                  {line}
                </span>
              ))}
            </SummaryRow>
          ) : null}
        </dl>

        {maps ? (
          /* Stacked and 165 wide on a phone — the frame keeps them left of the
             card's own text column rather than stretching them across it —
             and side by side at 197 from `md` up. */
          <div className="mt-5 flex flex-col gap-[18px] md:mt-6 md:flex-row md:justify-center md:gap-8">
            {venue.googleMapsUrl ? (
              <MapLink href={venue.googleMapsUrl}>Google Карты</MapLink>
            ) : null}
            {venue.yandexMapsUrl ? (
              <MapLink href={venue.yandexMapsUrl}>Яндекс Карты</MapLink>
            ) : null}
          </div>
        ) : null}
      </div>

      <LandingCtaButton cta={cta} applyPath={applyPath} />
    </div>
  );
}
