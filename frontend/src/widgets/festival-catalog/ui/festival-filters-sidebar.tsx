import { useId, useState } from "react";
import type {
  CatalogFilterOptions,
  CatalogFilters,
  ParticipationMode,
  PublicStatus,
} from "@/features/festival-catalog";
import {
  catalogStatusConfig,
  PARTICIPATION_MODES,
  participationModeLabel,
} from "@/features/festival-catalog";
import { cn } from "@/shared/lib";
import { Checkbox, DatePicker, FiltersIcon } from "@/shared/ui";

/**
 * The two date fields, which the frame draws smaller and plainer than the form
 * controls `DatePicker` is built for: 120×28 on a phone and 150×28 on a desktop,
 * both on a 5px corner, a 30%-strength hairline, and a 12px placeholder. Written once and shared rather than repeated
 * on both, so the pair cannot drift apart.
 */
const DATE_FIELD =
  "w-[120px] gap-0 xl:w-[150px] [&_label]:font-heading [&_label]:text-base [&_label]:leading-snug [&_label]:text-foreground [&_input]:h-7 [&_input]:rounded-[5px] [&_input]:border-foreground/30 [&_input]:bg-background [&_input]:font-heading [&_input]:text-xs [&_input]:leading-4 [&_input]:placeholder:text-foreground/40 dark:[&_input]:placeholder:text-on-scrim-muted";

interface FilterGroupProps {
  label: string;
  children: React.ReactNode;
}

/** One titled block of checkboxes: `Категория`, `Город`, `Формат участия`. */
function FilterGroup({ label, children }: FilterGroupProps): React.JSX.Element {
  return (
    <div>
      <p className="font-heading font-bold text-foreground text-lg leading-snug">{label}</p>
      {/* 9px between the title and the first row and between rows — the frame's
          29px pitch for a 20px box. `space-y` rather than a gap on a flex column
          so the title keeps its own step down to the list. */}
      <ul className="mt-2.5 space-y-2.5">{children}</ul>
    </div>
  );
}

interface FilterOptionProps {
  checked: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function FilterOption({ checked, onToggle, children }: FilterOptionProps): React.JSX.Element {
  return (
    <li>
      <Checkbox
        checked={checked}
        onCheckedChange={onToggle}
        label={children}
        // The box is the frame's: 20px, the page colour on a «светлый база
        // ночная» hairline, 3px corner — the one place on the public side that is
        // not the brand's 15. Ticked it fills with the action violet through
        // `--brand` rather than `--primary`, which drifts lighter at night; the
        // frame paints the same violet in both themes.
        //
        // The edge is `--control-line` in both themes, not the page's own ink let
        // down. It used to be `--foreground` at 42% and nothing at all at night,
        // because the dark export repeated the light theme's near-black — which
        // on a near-black page is no edge. The frame answers that with a violet
        // grey light enough to show on either plate, so the box keeps its outline
        // in both.
        //
        // The tick is `свет` by day and the page's own near-black by night —
        // the colour the box had before it was ticked, so the mark reads as cut
        // out of the fill rather than drawn on top of it.
        //
        // Coloured through `[&_svg]` and not on the box: the indicator takes
        // `text-current`, so a colour set on the root reaches it only by
        // inheritance, and `--primary-foreground` from the variant got there
        // first. A descendant selector outranks both and lands on the glyph.
        className="size-[25px] shrink-0 rounded-[3px] border-control-line bg-background data-[state=checked]:border-brand data-[state=checked]:bg-brand xl:size-5 [&_svg]:text-brand-mark dark:[&_svg]:text-background"
        containerClassName="gap-0 [&>div]:gap-3.5 [&_label]:font-heading [&_label]:text-base [&_label]:leading-snug [&_label]:text-foreground"
      />
    </li>
  );
}

interface FestivalFiltersSidebarProps {
  filters: CatalogFilters;
  options: CatalogFilterOptions;
  onChange: (filters: CatalogFilters) => void;
  className?: string;
}

function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

/**
 * The catalogue's filters, as the frame draws them: a standing panel down the
 * left of the page rather than a tray that opens over the grid.
 *
 * **Checkboxes, not the chips this used to use.** A chip row answers "which of
 * these few" and collapses as soon as the options outgrow a line; the frame
 * lists every category, city and format one per row, where the eye can run down
 * them and the state of each is legible without reading its colour. That also
 * makes the panel honest about how much choice there is, which a wrapped chip
 * row hides.
 *
 * Collapsible, because on a short screen 584px of filters is most of the fold
 * and the grid beside it is what the visitor came for. Closed it keeps only its
 * header, so the column does not vanish and the page does not reflow sideways.
 */
export function FestivalFiltersSidebar({
  filters,
  options,
  onChange,
  className,
}: FestivalFiltersSidebarProps): React.JSX.Element {
  // State for the phone only. On a desktop the filters are a standing column and
  // there is nothing to collapse: the grid sits beside them, and folding them
  // away would leave an empty gutter rather than buying any room. So this starts
  // closed, the desktop ignores it, and no media query is read at render — the
  // breakpoint is the stylesheet's business, not the component's.
  const [open, setOpen] = useState(false);
  const bodyId = useId();

  return (
    // `aside`, not `section`: the panel is complementary to the catalogue rather
    // than a part of it — it narrows the grid beside it and carries no content of
    // its own. That is also what puts it in a screen reader's landmark list under
    // its own name, which is how it is reached without walking the page.
    <aside
      aria-label="Фильтры каталога"
      className={cn(
        // The plate — `--brand-pane`, a warm grey at just under a fifth by day,
        // «тёмный база ночная» at 60% by night — belongs to the whole column on a
        // desktop and to the opened body alone on a phone, where the trigger
        // above it is a band of its own.
        // Deliberately not pinned. The column is tall enough that following the
        // reader down would park it over most of the viewport, and the grid is
        // paged — six cards, not an endless scroll — so the filters are never
        // more than a screen behind.
        "xl:rounded-brand xl:bg-brand-pane xl:px-7 xl:py-5",
        className,
      )}
    >
      {/* Two elements for one label, because on a desktop there is no control to
          speak of: the filters never fold there, so a button would be a promise
          the layout does not keep — and one that assistive technology would read
          out as pressable. The phone gets the band, the desktop gets a plain
          heading, and only one of the two is ever in the tree.

          The icon trails the label on the band, which is a button and reads left
          to right, and leads on the heading, where the row titles the column
          under it. */}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={bodyId}
        className="flex h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-brand bg-brand-surface font-bold text-brand-mark outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring xl:hidden dark:bg-brand-line/70"
      >
        <FiltersIcon className="order-2 h-[30px] w-[42px] shrink-0" />
        <span className="font-heading text-base leading-snug">Фильтры</span>
      </button>

      {/* Regular weight, not bold: the frame sets the panel's own name lighter
          than the group titles under it, so it reads as a label for the column
          rather than as the first of its headings. «полупрозрачный текст» by day
          — the flat `#6E6A72` the frame paints, which `--muted-foreground`
          carries to within a point — and «свет полупрозрачный», white at 70%, by
          night. Neither is the page's ink let down: a 40% near-black vanished
          into the night plate, and full white overshot what the frame draws. The
          icon takes the same colour by inheritance, as it does in the export. */}
      <p className="-ml-2 hidden items-center gap-1.5 font-heading text-[1.75rem] text-muted-foreground leading-snug xl:flex dark:xl:text-on-scrim-muted">
        <FiltersIcon className="h-[30px] w-[42px] shrink-0" />
        Фильтры
      </p>

      <div
        id={bodyId}
        className={cn(
          "mt-4 space-y-5 rounded-brand bg-brand-pane px-7 py-5 xl:mt-8 xl:rounded-none xl:bg-transparent xl:p-0",
          // Hidden by a class and not the `hidden` attribute, so the desktop can
          // put it back: the attribute cannot be overridden by a breakpoint.
          !open && "hidden xl:block",
        )}
      >
        {/* Status leads, because it is the axis that decides whether anything
            below it is worth narrowing: a genre filter over a list of finished
            festivals answers the wrong question. Only the statuses the catalogue
            actually holds are offered. */}
        {options.statuses.length > 0 ? (
          <FilterGroup label="Статус">
            {options.statuses.map((option) => (
              <FilterOption
                key={option.value}
                checked={filters.statuses.includes(option.value as PublicStatus)}
                onToggle={() =>
                  onChange({
                    ...filters,
                    statuses: toggle(filters.statuses, option.value as PublicStatus),
                  })
                }
              >
                {catalogStatusConfig(option.value).label}
              </FilterOption>
            ))}
          </FilterGroup>
        ) : null}

        {options.categories.length > 0 ? (
          <FilterGroup label="Категория">
            {options.categories.map((option) => (
              <FilterOption
                key={option.value}
                checked={filters.categories.includes(option.value)}
                onToggle={() =>
                  onChange({ ...filters, categories: toggle(filters.categories, option.value) })
                }
              >
                {option.value}
              </FilterOption>
            ))}
          </FilterGroup>
        ) : null}

        {options.cities.length > 0 ? (
          <FilterGroup label="Город">
            {options.cities.map((option) => (
              <FilterOption
                key={option.value}
                checked={filters.cities.includes(option.value)}
                onToggle={() =>
                  onChange({ ...filters, cities: toggle(filters.cities, option.value) })
                }
              >
                {option.value}
              </FilterOption>
            ))}
          </FilterGroup>
        ) : null}

        <FilterGroup label="Формат участия">
          {PARTICIPATION_MODES.map((mode: ParticipationMode) => (
            <FilterOption
              key={mode}
              checked={filters.modes.includes(mode)}
              onToggle={() => onChange({ ...filters, modes: toggle(filters.modes, mode) })}
            >
              {participationModeLabel(mode)}
            </FilterOption>
          ))}
        </FilterGroup>

        <div>
          <p className="font-heading font-bold text-base text-foreground leading-snug">
            Даты проведения
          </p>
          <div className="mt-2.5 flex flex-wrap gap-x-11 gap-y-4">
            <DatePicker
              label="С"
              placeholder="Не раньше"
              value={filters.competitionFrom ?? ""}
              onChange={(value) => onChange({ ...filters, competitionFrom: value || null })}
              containerClassName={DATE_FIELD}
            />
            <DatePicker
              label="По"
              placeholder="Не позже"
              value={filters.competitionTo ?? ""}
              onChange={(value) => onChange({ ...filters, competitionTo: value || null })}
              containerClassName={DATE_FIELD}
            />
          </div>
        </div>
      </div>
    </aside>
  );
}
