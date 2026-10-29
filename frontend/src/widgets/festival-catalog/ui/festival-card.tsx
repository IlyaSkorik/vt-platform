import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import {
  catalogStatusConfig,
  type Festival,
  formatAgeRange,
  formatPeriod,
  participationModeLabel,
  resolveMediaUrl,
} from "@/features/festival-catalog";
import { ROUTES } from "@/shared/config";
import { cn, festivalPath } from "@/shared/lib";
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
  const ageRange = formatAgeRange(festival);

  const detailPath = festivalPath(festival, detailBasePath);
  const cabinetApplyPath = `${festivalPath(festival, ROUTES.cabinetCompetitions)}/apply`;
  // A visitor who is not signed in is not stopped at the door: the login screen
  // is told where they were going and hands them back to it.
  const applyPath = isAuthenticated
    ? cabinetApplyPath
    : `${ROUTES.login}?next=${encodeURIComponent(cabinetApplyPath)}`;

  return (
    // 295px and centred while there is one column, which is narrower than the
    // page's own gutter allows: the frame insets the cards to 41/39 on a 375px
    // screen while the search and filter bands run to 14. The card is the one
    // thing on the page with a margin of its own, and at the full width it read
    // as a panel rather than as a tile.
    //
    // The outline is «тёмный акцент» by day and «тёмный база ночная» by night: on
    // a near-black page the day's violet is the loudest thing on screen, and six
    // of these at once turned the grid into a cage.
    <article className="mx-auto flex h-full w-full max-w-[295px] flex-col gap-3 rounded-brand border-2 border-brand-line p-3.5 md:max-w-none xl:p-2.5 dark:border-brand-track">
      <Link
        to={detailPath}
        aria-label={`Подробнее: ${festival.title}`}
        className="block overflow-hidden rounded-brand bg-muted outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="aspect-[263/146] xl:aspect-[406/200]">
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

      <h3 className="line-clamp-2 font-heading font-semibold text-foreground text-sm leading-snug xl:text-lg">
        <Link
          to={detailPath}
          className="rounded-sm outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {festival.title}
        </Link>
      </h3>

      {/* A description list, because each row is a labelled fact rather than a
          sentence. The icon is the label, so it carries the text the `dt` would
          have — otherwise a screen reader reads out two bare values.

          «полупрозрачный текст» by day — a flat `#6E6A72`, which
          `--muted-foreground` carries to within a point, not the card's ink let
          down — and «свет полупрозрачный» at night. The same pair the landing's
          own festival card wears. */}
      <dl className="space-y-1 font-heading text-muted-foreground text-sm leading-snug xl:text-lg dark:text-on-scrim-muted">
        {place ? (
          <div className="flex items-center gap-1.5">
            <dt className="shrink-0">
              <MapPinIcon className="size-[19px] xl:size-5" aria-hidden="true" />
              <span className="sr-only">Место проведения</span>
            </dt>
            <dd className="truncate">{place}</dd>
          </div>
        ) : null}
        {period ? (
          <div className="flex items-center gap-1.5">
            <dt className="shrink-0">
              <CalendarIcon className="size-[19px] xl:size-5" aria-hidden="true" />
              <span className="sr-only">Даты проведения</span>
            </dt>
            <dd className="truncate">{period}</dd>
          </div>
        ) : null}
      </dl>

      {/* `my-auto`, so the slack a short card leaves is split above and below the
          nominations rather than all falling under them. The actions stay on the
          floor without `mt-auto` of their own: once this row takes the free space
          symmetrically, there is none left to push them down with. */}
      {festival.categories.length > 0 ? (
        <ul className="my-auto flex flex-wrap gap-2">
          {festival.categories.map((category) => (
            <li key={category}>
              {/* A hairline against the landing's two pixels: the catalogue shows
                  six of these at once and the heavier line turned the lower half
                  of every card into a grid of boxes. The exception is the phone in
                  the light theme, where the frame thickens it back to two —
                  «светлый акцент» on `свет` is pale enough that one pixel at 10px
                  type stopped reading as an outline at all. */}
              <Badge
                variant="brand"
                size="md"
                className="h-[21px] border-2 px-2 font-heading font-normal text-[10px] leading-[14px] xl:h-6.5 xl:border xl:text-xs xl:leading-4 dark:border dark:border-brand-control"
              >
                {category}
              </Badge>
            </li>
          ))}
        </ul>
      ) : null}

      {/* Between the nominations and the actions, which is where the frame puts
          it: the last thing read before deciding whether to apply, and the one
          fact on the card that can rule the festival out outright.

          Set in the card's own ink at full strength rather than the let-down
          grey the place and dates wear — it is a condition of entry, not a
          caption. Dropped entirely when the organizer has declared no age
          categories: an empty «Возрастная категория: » reads as a bug, and a
          made-up «для всех» would be a claim nobody made.

          Outside the `my-auto` chip row on purpose, so the card's spare height
          still splits around the nominations and this line stays put above the
          buttons. */}
      {ageRange ? (
        <p className="font-heading text-foreground text-sm leading-snug xl:text-lg">
          Возрастная категория: {ageRange}
        </p>
      ) : null}

      {/* The actions sit further in than everything above them — the frame insets
          them about 26px past the card's own padding, so the pair reads as a
          footer to the tile rather than as two more rows of it, and leaves 25px
          under the last one: the card's own 10 plus 15 here. */}
      <div
        className={cn(
          "flex flex-col gap-[7.5px] px-2 pb-1 xl:gap-[7px] xl:px-[26px] xl:pb-[15px]",
          // No top padding and no `mt-auto` while the nominations are there:
          // those two are what the equal gaps above and below them are measured
          // against, and the chips' `my-auto` is the only claim on the card's
          // spare height, so it splits it in two and this block lands on the
          // floor anyway. With no nominations to centre there is no claim at all,
          // and it needs `mt-auto` back or it floats up under the dates.
          festival.categories.length === 0 && "mt-auto",
        )}
      >
        {status.apply.enabled ? (
          <Button
            asChild
            className="relative h-[37px] w-full justify-center rounded-brand font-heading font-bold text-base leading-snug hover:bg-brand-press xl:h-[39px] xl:text-lg [&_svg]:size-[25px] xl:[&_svg]:size-7 dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-press"
          >
            {/* The label is centred in the button and the arrow hangs off the
                right of it, which is why the arrow is taken out of the flow
                rather than laid out beside the text: in a row the two would be
                centred as a pair, and the label would sit left of the middle by
                half the arrow.

                It is also sized from the button and not on the icon — the `size`
                variant carries `[&_svg]:size-5`, a descendant selector that
                outranks a plain class on the `svg` itself, so setting it there
                left the glyph silently at 20px. */}
            <Link to={applyPath}>
              {status.apply.label}
              <ArrowRightIcon className="-translate-y-1/2 absolute top-1/2 right-4 xl:right-10" />
            </Link>
          </Button>
        ) : (
          /* Not an action but a statement in an action's place — «Регистрация
             закрыта», «Фестиваль идёт». Outlined in «светлый акцент» at half
             strength by day and `свет` at 30% by night — the day's violet is a
             colour the night page uses for things that *do* something — and set
             in the regular weight, so it reads as the quietest thing on the card; `disabled:opacity-100` because the variant's own
             fade on top of a 50% line left it barely visible, and this is meant
             to be read, not merely seen to be unavailable. */
          <Button
            disabled
            variant="outline"
            className="h-[37px] w-full rounded-brand border-brand-line-soft/50 bg-transparent font-heading text-base text-foreground leading-snug disabled:opacity-100 xl:h-[39px] xl:text-lg dark:border-on-scrim/30"
          >
            {status.apply.label}
          </Button>
        )}

        {/* «Подробнее» keeps its place in both cases and changes only its line:
            the quiet «тёмный акцент» while there is a real action above it, and
            «Акцентище» in bold once there is not — it is then the only thing on
            the card that still leads anywhere. */}
        <Button
          asChild
          variant="outline"
          className={cn(
            "h-[37px] w-full rounded-brand bg-transparent font-heading text-base text-foreground leading-snug hover:text-foreground xl:h-[39px] xl:text-lg",
            status.apply.enabled
              ? "border-brand-line font-bold hover:bg-brand-line-soft/20 xl:font-normal dark:border-brand-control dark:hover:bg-brand-control/20"
              : "border-brand font-bold hover:bg-brand/10",
          )}
        >
          <Link to={detailPath}>Подробнее</Link>
        </Button>
      </div>
    </article>
  );
}
