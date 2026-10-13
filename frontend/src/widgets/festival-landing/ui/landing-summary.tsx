import { Banknote, ExternalLink, Map as MapIcon, Users } from "lucide-react";
import { formatPeriod } from "@/features/festival-catalog";
import {
  type FestivalDetail,
  type FestivalVenue,
  formatFromPrice,
  heroBlock,
  landingCta,
} from "@/features/festival-landing";
import { Button, CalendarIcon, MapPinIcon } from "@/shared/ui";
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
      <dt className="flex items-center gap-4 text-foreground/60">
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
 * One of the two map links. An outlined 197×39 plate on a 10px corner — the one
 * place on the page that is *not* the brand's 15, which is why the radius is
 * written out rather than taken from `rounded-brand`.
 */
function MapLink({ href, children }: MapLinkProps): React.JSX.Element {
  return (
    <Button
      asChild
      variant="outline"
      className="h-[34px] w-full rounded-[10px] border-brand-line bg-background font-heading font-normal text-foreground text-sm leading-[19px] shadow-none md:h-[39px] md:w-[197px] md:text-base md:leading-[22px]"
    >
      <a href={href} target="_blank" rel="noopener noreferrer">
        <MapIcon className="size-5 md:size-6" aria-hidden="true" />
        {children}
        <ExternalLink className="size-4" aria-hidden="true" />
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
 * **Price and formats are kept, though the frame does not draw them.** They are
 * the two facts a visitor needs *before* opening the wizard, and they have
 * nowhere else to go on the page — so they continue the same labelled list
 * under the address rather than being dropped to match the mock exactly.
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
  const price = formatFromPrice(festival.pricing);
  const formatNames = festival.formats.map((format) => format.name);
  const { venue } = festival.contacts;
  const lines = venueLines(venue, festival.city);
  const maps = venue.googleMapsUrl || venue.yandexMapsUrl;

  return (
    <div className="flex flex-col gap-2.5">
      {/* `bg-background`, not `bg-card`: the frame fills the panel with `свет`
          — the page's own colour — and lets the two-pixel «тёмный акцент»
          outline be the whole of what separates it from the page. */}
      <div className="rounded-brand border-2 border-brand-line bg-background px-4 pt-3 pb-6 md:px-5">
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
          {formatNames.length > 0 ? (
            <SummaryRow icon={Users} label="Форматы участия">
              {formatNames.join(", ")}
            </SummaryRow>
          ) : null}
          {price ? (
            <SummaryRow icon={Banknote} label="Стоимость участия">
              {price}
            </SummaryRow>
          ) : null}
        </dl>

        {maps ? (
          <div className="mt-5 flex flex-col gap-2.5 md:mt-6 md:flex-row md:justify-center md:gap-8">
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
