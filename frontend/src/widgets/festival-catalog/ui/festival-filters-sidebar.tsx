import { useId, useState } from "react";
import type {
  CatalogFilterOptions,
  CatalogFilters,
  ParticipationMode,
} from "@/features/festival-catalog";
import { PARTICIPATION_MODES, participationModeLabel } from "@/features/festival-catalog";
import { cn } from "@/shared/lib";
import { Checkbox, DatePicker, FiltersIcon } from "@/shared/ui";

/**
 * The two date fields, which the frame draws smaller and plainer than the form
 * controls `DatePicker` is built for: 150×28 on a 5px corner, a 30%-strength
 * hairline, and a 12px placeholder. Written once and shared rather than repeated
 * on both, so the pair cannot drift apart.
 */
const DATE_FIELD =
  "w-[150px] gap-0 [&_label]:font-heading [&_label]:text-base [&_label]:leading-snug [&_label]:text-foreground [&_input]:h-7 [&_input]:rounded-[5px] [&_input]:border-foreground/30 [&_input]:bg-background [&_input]:font-heading [&_input]:text-xs [&_input]:leading-4 [&_input]:placeholder:text-foreground/40 dark:[&_input]:placeholder:text-on-scrim-muted";

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
        // The box is the frame's: 20px, `свет` on a 42%-strength hairline, 3px
        // corner — the one place on the public side that is not the brand's 15.
        className="size-5 shrink-0 rounded-[3px] border-foreground/42 bg-background"
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
  const [open, setOpen] = useState(true);
  const bodyId = useId();

  return (
    // `aside`, not `section`: the panel is complementary to the catalogue rather
    // than a part of it — it narrows the grid beside it and carries no content of
    // its own. That is also what puts it in a screen reader's landmark list under
    // its own name, which is how it is reached without walking the page.
    <aside
      aria-label="Фильтры каталога"
      className={cn(
        // `--brand-pane`: a warm grey at just under a fifth by day, «тёмный база
        // ночная» at 60% by night. Over the page it reads as a panel without
        // being a surface.
        // `sticky` from `xl`, where the panel has a column of its own: the grid
        // beside it is pages long, and filters that scroll away are filters the
        // reader has to come back up for. `top` clears the sticky header (60px)
        // and leaves the page's own 27px of air above it.
        "rounded-brand bg-brand-pane px-7 py-5 xl:sticky xl:top-[87px]",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={bodyId}
        className="-ml-2 flex w-full cursor-pointer items-center gap-1.5 rounded-sm text-foreground/40 outline-none transition-colors hover:text-foreground/60 focus-visible:ring-2 focus-visible:ring-ring dark:text-on-scrim dark:hover:text-on-scrim-muted"
      >
        <FiltersIcon className="h-[30px] w-[42px] shrink-0" />
        {/* Regular weight, not bold: the frame sets the panel's own name lighter
            than the group titles under it, so it reads as a label for the column
            rather than as the first of its headings. It is let down to 40% by day
            and run at full `свет` by night, where the plate behind it is dark
            enough that a 40% label would have disappeared into it. */}
        <span className="font-heading text-[1.75rem] leading-snug">Фильтры</span>
      </button>

      <div id={bodyId} hidden={!open} className="mt-8 space-y-5">
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
