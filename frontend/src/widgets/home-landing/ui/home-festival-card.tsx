import { Link } from "react-router";
import {
  type Festival,
  formatPeriod,
  participationModeLabel,
  resolveMediaUrl,
} from "@/features/festival-catalog";
import { Badge, CalendarIcon, MapPinIcon, PosterImage } from "@/shared/ui";

interface HomeFestivalCardProps {
  festival: Festival;
  /** Where the whole card leads. Computed by the caller so this stays route-agnostic. */
  to: string;
}

/**
 * The place-and-format line, which the design prints as one string («Минск,
 * Очно»). Either half can be missing — a festival with no city, an online-only
 * one still being set up — so the pieces are filtered rather than joined blind,
 * which is what used to leave a bare comma on the card.
 */
function placeLine(festival: Festival): string | null {
  const mode = festival.modes[0];
  const parts = [festival.city, mode ? participationModeLabel(mode) : null].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : null;
}

/**
 * The landing's festival tile — the catalog's card, restated in the brand's own
 * terms for the one page that is marketing rather than product.
 *
 * Deliberately **not** `widgets/festival-catalog`'s `FestivalCard`. That one is
 * a working control: it carries the status badge, the price, the closing-soon
 * warning, the organiser's avatar and two separate actions, because the person
 * reading it is choosing between twenty of them. This is an advertisement for
 * four facts — what, where, when, which nominations — and one action, which is
 * the whole card. Folding the two into one component would mean a card that is
 * mostly props about which half to hide.
 *
 * The whole tile is a single link rather than a card with a link inside it: there
 * is exactly one destination, and splitting it into a clickable title and a
 * non-clickable body gives a pointer three dead zones over a 400px target.
 */
export function HomeFestivalCard({ festival, to }: HomeFestivalCardProps): React.JSX.Element {
  const cover = resolveMediaUrl(festival.coverImage);
  const place = placeLine(festival);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);

  return (
    // The wrapper is what the pointer hovers; the link is what moves. Hovering
    // the moving element is a loop: the lift carries its own hit area up with
    // it, the cursor near the bottom edge falls out, the card drops back, the
    // cursor is inside again — and the card shivers for as long as you hold the
    // pointer there. A still box the size of the slot breaks the cycle, because
    // nothing the lift does can change what the pointer is over.
    // 250px wide and centred in its slide on the phone, as the frame draws it —
    // a card the full width of a 375px screen is a poster, not a tile, and the
    // one next to it would start showing past the edge.
    <div className="group/tile mx-auto h-full w-full max-w-[250px] md:max-w-none">
      <Link
        to={to}
        className="flex h-full flex-col gap-2 rounded-brand md:gap-3 border-2 border-brand-line bg-card p-[11px] outline-none md:p-3.5 transition-[box-shadow,background-color,transform] duration-[var(--duration-slow)] ease-decelerate focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 group-hover/tile:shadow-glow-strong group-hover/tile:-translate-y-0.5 dark:bg-transparent dark:group-hover/tile:bg-brand-line-soft/5"
      >
        {/* A shade wider on the phone — 224×125 against the desktop's 299×180 —
          because the frame crops it that way rather than scaling one ratio down.
          Either way the poster does not zoom under the pointer: it is cropped to
          the card already, so scaling pushed the subject out of frame on exactly
          the tiles where the subject was the point, and the card's own lift and
          halo are enough to say the tile is live. */}
        <div className="aspect-[224/125] overflow-hidden rounded-brand bg-muted md:aspect-[299/180] dark:bg-on-scrim/9">
          {cover ? (
            <PosterImage
              src={cover}
              alt={`Афиша фестиваля ${festival.title}`}
              loading="lazy"
              // `cover`, against `PosterImage`'s own `contain`. That default is
              // right in the catalogue, where a poster is a document and cutting
              // its edges can cut the text printed on it. Here the tile is an
              // advertisement: the frame draws a filled rectangle, and `contain`
              // left bars down the sides of every cover whose ratio was not the
              // box's — which is most of them, since the box is a different shape
              // in the two layouts.
              imageClassName="object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center px-4 text-center font-heading text-muted-foreground text-xs">
              Афиша скоро появится
            </div>
          )}
        </div>

        <h3 className="line-clamp-2 font-heading font-bold text-foreground text-sm leading-snug md:text-base">
          {festival.title}
        </h3>

        {/* A description list, because each row is a labelled fact rather than a
          sentence. The icon is the label, so it carries the text the `dt` would
          have — otherwise a screen reader reads out two bare values.

          The two glyphs are the frame's own, 18×22, not Lucide's near-misses.
          Colour lives on the row rather than inside the paths, so icon and value
          are always the same ink and one token moves both: «полупрозрачный
          текст» by day — `#211929` at 40% — and «свет полупрозрачный» at night,
          which is white at 70% over a dark tile rather than a dimmed black. */}
        <dl className="space-y-1 font-heading text-foreground/40 text-sm leading-snug md:space-y-1.5 md:text-base dark:text-on-scrim-muted">
          {place ? (
            <div className="flex items-center gap-2">
              <dt className="shrink-0">
                <MapPinIcon className="h-[19px] w-4 md:h-5.5 md:w-4.5" aria-hidden="true" />
                <span className="sr-only">Место проведения</span>
              </dt>
              <dd className="truncate">{place}</dd>
            </div>
          ) : null}
          {period ? (
            <div className="flex items-center gap-2">
              <dt className="shrink-0">
                <CalendarIcon className="h-[19px] w-4 md:h-5.5 md:w-4.5" aria-hidden="true" />
                <span className="sr-only">Даты проведения</span>
              </dt>
              <dd className="truncate">{period}</dd>
            </div>
          ) : null}
        </dl>

        {/* Filled from the top of the block, not pushed to the bottom of the card.
          Cards in a row are all the height of the tallest, so a tile whose
          nominations fit on one line used to have `mt-auto` shove them to the
          floor and open a hole between the dates and the chips. Left alone they
          sit under the dates where they belong and the slack collects at the
          bottom, where it reads as margin rather than as a gap. */}
        {festival.categories.length > 0 ? (
          <ul className="flex flex-wrap gap-2 pt-1">
            {festival.categories.map((category) => (
              <li key={category}>
                {/* 21px tall at 10/14 on the phone, 26px at 12/16 on the
                    desktop. Shape and weight are the `brand` variant's:
                    a 2px outline on the brand's 15px corner, transparent, label
                    in the page's own ink. Only the outline colour is overridden,
                    and only at night — «светлый акцент» `#B196D0` by day,
                    «светлый база ночная» `#88779B` after dark, which is the one
                    place the chip parts company with the glow it shares a token
                    with in the light theme. */}
                <Badge
                  variant="brand"
                  size="md"
                  className="h-[21px] px-2 font-heading font-normal text-[10px] leading-[14px] md:h-6.5 md:text-xs md:leading-4 dark:border-brand-control"
                >
                  {category}
                </Badge>
              </li>
            ))}
          </ul>
        ) : null}
      </Link>
    </div>
  );
}
