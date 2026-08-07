import { RotateCcw } from "lucide-react";
import type {
  CatalogFilterOptions,
  CatalogFilters,
  ParticipationMode,
  RegistrationFilter,
} from "@/features/festival-catalog";
import {
  hasActiveFilters,
  PARTICIPATION_MODES,
  participationModeLabel,
} from "@/features/festival-catalog";
import { cn } from "@/shared/lib";
import { Button, Card, CardContent, DatePicker } from "@/shared/ui";

interface FilterChipProps {
  active: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function FilterChip({ active, onToggle, children }: FilterChipProps): React.JSX.Element {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onToggle}
      className={cn(
        "rounded-full border px-3 py-1 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-background text-foreground hover:bg-muted",
      )}
    >
      {children}
    </button>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

const REGISTRATION_OPTIONS: { value: RegistrationFilter; label: string }[] = [
  { value: "OPEN", label: "Открыта" },
  { value: "CLOSING_SOON", label: "Закрывается" },
];

interface FestivalFiltersPanelProps {
  filters: CatalogFilters;
  options: CatalogFilterOptions;
  onChange: (filters: CatalogFilters) => void;
  onReset: () => void;
}

function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

/** The full, composable filters panel (registration, format, dates, location, category). */
export function FestivalFiltersPanel({
  filters,
  options,
  onChange,
  onReset,
}: FestivalFiltersPanelProps): React.JSX.Element {
  return (
    <Card>
      <CardContent className="grid gap-5 pt-6 lg:grid-cols-2">
        <FilterGroup label="Регистрация">
          {REGISTRATION_OPTIONS.map((option) => (
            <FilterChip
              key={option.value}
              active={filters.registration.includes(option.value)}
              onToggle={() =>
                onChange({ ...filters, registration: toggle(filters.registration, option.value) })
              }
            >
              {option.label}
            </FilterChip>
          ))}
        </FilterGroup>

        <FilterGroup label="Формат участия">
          {PARTICIPATION_MODES.map((mode: ParticipationMode) => (
            <FilterChip
              key={mode}
              active={filters.modes.includes(mode)}
              onToggle={() => onChange({ ...filters, modes: toggle(filters.modes, mode) })}
            >
              {participationModeLabel(mode)}
            </FilterChip>
          ))}
        </FilterGroup>

        {options.categories.length > 0 ? (
          <FilterGroup label="Категория">
            {options.categories.map((option) => (
              <FilterChip
                key={option.value}
                active={filters.categories.includes(option.value)}
                onToggle={() =>
                  onChange({ ...filters, categories: toggle(filters.categories, option.value) })
                }
              >
                {option.value}
              </FilterChip>
            ))}
          </FilterGroup>
        ) : null}

        {options.cities.length > 0 ? (
          <FilterGroup label="Город">
            {options.cities.map((option) => (
              <FilterChip
                key={option.value}
                active={filters.cities.includes(option.value)}
                onToggle={() =>
                  onChange({ ...filters, cities: toggle(filters.cities, option.value) })
                }
              >
                {option.value}
              </FilterChip>
            ))}
          </FilterGroup>
        ) : null}

        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">Даты проведения</p>
          <div className="flex flex-wrap items-end gap-3">
            <DatePicker
              label="С"
              placeholder="Не раньше"
              value={filters.competitionFrom ?? ""}
              onChange={(value) => onChange({ ...filters, competitionFrom: value || null })}
              containerClassName="w-48"
            />
            <DatePicker
              label="По"
              placeholder="Не позже"
              value={filters.competitionTo ?? ""}
              onChange={(value) => onChange({ ...filters, competitionTo: value || null })}
              containerClassName="w-48"
            />
          </div>
        </div>

        <div className="flex items-end justify-end lg:col-span-2">
          <Button
            type="button"
            variant="ghost"
            onClick={onReset}
            disabled={!hasActiveFilters(filters)}
            leftIcon={<RotateCcw className="size-4" aria-hidden="true" />}
          >
            Сбросить
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
