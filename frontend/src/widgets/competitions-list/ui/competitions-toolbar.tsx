import { Search } from "lucide-react";
import {
  type CompetitionSortOption,
  type CompetitionStatusFilter,
  SORT_OPTIONS,
  STATUS_FILTER_OPTIONS,
} from "@/features/competitions";
import { Input, Select } from "@/shared/ui";

interface CompetitionsToolbarProps {
  search: string;
  status: CompetitionStatusFilter;
  sort: CompetitionSortOption;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: CompetitionStatusFilter) => void;
  onSortChange: (value: CompetitionSortOption) => void;
}

export function CompetitionsToolbar({
  search,
  status,
  sort,
  onSearchChange,
  onStatusChange,
  onSortChange,
}: CompetitionsToolbarProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
      <Input
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        placeholder="Поиск фестивалей…"
        leadingIcon={<Search aria-hidden="true" />}
        containerClassName="w-full lg:max-w-sm"
        aria-label="Поиск фестивалей"
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:ml-auto lg:flex lg:items-center">
        <Select
          value={status}
          onValueChange={(value) => onStatusChange(value as CompetitionStatusFilter)}
          placeholder="Статус"
          options={STATUS_FILTER_OPTIONS.map((option) => ({
            value: option.value,
            label: option.label,
          }))}
          className="w-full sm:w-52"
        />
        <Select
          value={sort}
          onValueChange={(value) => onSortChange(value as CompetitionSortOption)}
          placeholder="Сортировка"
          options={SORT_OPTIONS.map((option) => ({
            value: option.value,
            label: option.label,
          }))}
          className="w-full sm:w-40"
        />
      </div>
    </div>
  );
}
