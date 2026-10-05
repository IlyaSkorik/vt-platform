import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import {
  catalogStatusConfig,
  type Festival,
  formatPeriod,
  participationModeLabel,
  resolveMediaUrl,
} from "@/features/festival-catalog";
import { ROUTES } from "@/shared/config";
import { festivalPath } from "@/shared/lib";
import { ArrowRightIcon, Badge, Button, CalendarIcon, MapPinIcon, PosterImage } from "@/shared/ui";

interface FestivalCardProps {
  festival: Festival;
  now: Date;
  detailBasePath?: string;
}

/**
 * The place-and-format line the frame prints as one string («Минск, Очно»).
 * Either half can be missing, so the pieces are filtered rather than joined
 * blind — that is what used to leave a bare comma on the card.
 */
function placeLine(festival: Festival): string | null {
  const mode = festival.modes[0];
  const parts = [festival.city, mode ? participationModeLabel(mode) : null].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : null;
}

/**
 * A single festival tile — the atom of the catalogue grid.
 *
 * **Four facts and two actions, and nothing else.** The card used to carry a
 * status badge, a price chip, a closing-soon warning, the organiser's avatar and
 * the season as well; the frame drops every one of them. That is a judgement
 * about where they belong rather than about their worth: all of it is on the
 * festival's own page, one click away, and a tile that answers eleven questions
 * at a glance answers none of them. What survives is what a reader scans *by* —
 * the name, where and when, which nominations — plus the two things they can do.
 *
 * The chips are the nominations, not the participation formats. The format is
 * already in the line above, and repeating it below as a chip spent the one row
 * the frame gives to what the festival is actually about.
 */
export function FestivalCard({
  festival,
  detailBasePath = ROUTES.cabinetCompetitions,
}: FestivalCardProps): React.JSX.Element {
  const { isAuthenticated } = useAuth();
  const status = catalogStatusConfig(festival.status);
  const cover = resolveMediaUrl(festival.coverImage);
  const place = placeLine(festival);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);

  const detailPath = festivalPath(festival, detailBasePath);
  const cabinetApplyPath = `${festivalPath(festival, ROUTES.cabinetCompetitions)}/apply`;
  // A visitor who is not signed in is not stopped at the door: the login screen
  // is told where they were going and hands them back to it.
  const applyPath = isAuthenticated
    ? cabinetApplyPath
    : `${ROUTES.login}?next=${encodeURIComponent(cabinetApplyPath)}`;

  return (
    // The outline is «тёмный акцент» by day and «тёмный база ночная» by night: on a
    // near-black page the day's violet is the loudest thing on screen, and six of
    // these at once turned the grid into a cage.
    <article className="flex h-full flex-col gap-3 rounded-brand border-2 border-brand-line p-2.5 dark:border-brand-track">
      <Link
        to={detailPath}
        aria-label={`Подробнее: ${festival.title}`}
        className="block overflow-hidden rounded-brand bg-muted outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="aspect-[406/200]">
          {cover ? (
            // `cover`, against `PosterImage`'s own `contain`: the frame draws a
            // filled rectangle, and fitting left bars down the sides of every
            // poster whose ratio was not the box's.
            <PosterImage
              src={cover}
              alt={`Афиша фестиваля ${festival.title}`}
              loading="lazy"
              imageClassName="object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center px-4 text-center font-heading text-muted-foreground text-sm">
              Афиша скоро появится
            </div>
          )}
        </div>
      </Link>

      <h3 className="line-clamp-2 font-heading font-bold text-foreground text-lg leading-snug">
        <Link
          to={detailPath}
          className="rounded-sm outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {festival.title}
        </Link>
      </h3>

      {/* A description list, because each row is a labelled fact rather than a
          sentence. The icon is the label, so it carries the text the `dt` would
          have — otherwise a screen reader reads out two bare values. */}
      <dl className="space-y-1 font-heading text-foreground/40 text-lg leading-snug dark:text-on-scrim-muted">
        {place ? (
          <div className="flex items-center gap-1.5">
            <dt className="shrink-0">
              <MapPinIcon className="size-5" aria-hidden="true" />
              <span className="sr-only">Место проведения</span>
            </dt>
            <dd className="truncate">{place}</dd>
          </div>
        ) : null}
        {period ? (
          <div className="flex items-center gap-1.5">
            <dt className="shrink-0">
              <CalendarIcon className="size-5" aria-hidden="true" />
              <span className="sr-only">Даты проведения</span>
            </dt>
            <dd className="truncate">{period}</dd>
          </div>
        ) : null}
      </dl>

      {festival.categories.length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {festival.categories.map((category) => (
            <li key={category}>
              {/* A hairline here against the landing's two pixels: the catalogue
                  shows six of these at once and the heavier line turned the lower
                  half of every card into a grid of boxes. */}
              <Badge
                variant="brand"
                size="md"
                className="h-6.5 border px-2 font-heading font-normal text-xs leading-4 dark:border-brand-control"
              >
                {category}
              </Badge>
            </li>
          ))}
        </ul>
      ) : null}

      {/* The actions sit further in than everything above them — the frame insets
          them about 26px past the card's own padding, so the pair reads as a
          footer to the tile rather than as two more rows of it, and leaves 25px
          under the last one — the card's own 10 plus 15 here. `mt-auto` keeps
          them on the floor however tall the card's text turns out to be. */}
      <div className="mt-auto space-y-[7px] px-[26px] pt-8 pb-[15px]">
        {status.apply.visible ? (
          status.apply.enabled ? (
            <Button
              asChild
              className="relative h-[39px] w-full justify-center rounded-brand font-heading font-bold text-lg leading-snug hover:bg-brand-line [&_svg]:size-7 dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
            >
              {/* The label is centred in the button and the arrow hangs off the
                  right of it, which is why the arrow is taken out of the flow
                  rather than laid out beside the text: in a row the two would be
                  centred as a pair, and the label would sit left of the middle by
                  half the arrow. 40px in from the edge: the frame puts it 53 from
                  the right of a 353px button, and this one stretches to the card,
                  so the distance is kept closer to the label it trails.

                  It is also sized from the button and not on the icon — the
                  `size` variant carries `[&_svg]:size-5`, a descendant selector
                  that outranks a plain class on the `svg` itself, so setting it
                  there left the glyph silently at 20px. */}
              <Link to={applyPath}>
                {status.apply.label}
                <ArrowRightIcon className="-translate-y-1/2 absolute top-1/2 right-10" />
              </Link>
            </Button>
          ) : (
            <Button
              disabled
              className="h-[39px] w-full rounded-brand font-heading font-bold text-lg leading-snug"
            >
              {status.apply.label}
            </Button>
          )
        ) : null}
        <Button
          asChild
          variant="outline"
          className="h-[39px] w-full rounded-brand border-brand-line bg-transparent font-heading text-foreground text-lg leading-snug hover:bg-brand-line-soft/20 hover:text-foreground dark:border-brand-control dark:hover:bg-brand-control/20"
        >
          <Link to={detailPath}>Подробнее</Link>
        </Button>
      </div>
    </article>
  );
}
