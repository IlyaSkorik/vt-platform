import { Search, SlidersHorizontal } from "lucide-react";
import type { CatalogSort } from "@/features/festival-catalog";
import { Badge, Button, Input, Select } from "@/shared/ui";

const SORT_OPTIONS: { value: CatalogSort; label: string }[] = [
  { value: "NEWEST", label: "Сначала новые" },
  { value: "CLOSING_SOON", label: "Регистрация закрывается" },
  { value: "COMPETITION_DATE", label: "По дате проведения" },
  { value: "ALPHABETICAL", label: "По алфавиту" },
];

interface FestivalCatalogToolbarProps {
  query: string;
  onQueryChange: (query: string) => void;
  sort: CatalogSort;
  onSortChange: (sort: CatalogSort) => void;
  filtersOpen: boolean;
  onToggleFilters: () => void;
  activeFilterCount: number;
}

/** Search + sort + filter toggle — the top bar above the grid. */
export function FestivalCatalogToolbar({
  query,
  onQueryChange,
  sort,
  onSortChange,
  filtersOpen,
  onToggleFilters,
  activeFilterCount,
}: FestivalCatalogToolbarProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="flex-1">
        <Input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по названию, городу или организатору"
          leadingIcon={<Search className="size-4" aria-hidden="true" />}
          aria-label="Поиск фестивалей"
          containerClassName="w-full"
        />
      </div>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant={filtersOpen ? "secondary" : "outline"}
          onClick={onToggleFilters}
          aria-expanded={filtersOpen}
          leftIcon={<SlidersHorizontal className="size-4" aria-hidden="true" />}
        >
          Фильтры
          {activeFilterCount > 0 ? (
            <Badge variant="primary" size="sm">
              {activeFilterCount}
            </Badge>
          ) : null}
        </Button>
        <Select
          options={SORT_OPTIONS}
          value={sort}
          onValueChange={(value) => onSortChange(value as CatalogSort)}
          aria-label="Сортировка"
          containerClassName="min-w-52"
        />
      </div>
    </div>
  );
}
