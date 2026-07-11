import { CalendarSearch, Frown, RotateCcw, SearchX } from "lucide-react";
import { Button, EmptyState } from "@/shared/ui";

/** Nothing published yet — the catalog itself is empty. */
export function CatalogNoFestivals(): React.JSX.Element {
  return (
    <EmptyState
      icon={<CalendarSearch aria-hidden="true" />}
      title="Пока нет фестивалей"
      description="Как только организаторы опубликуют события, они появятся здесь. Загляните позже."
    />
  );
}

interface CatalogNoResultsProps {
  onReset: () => void;
  reason: "search" | "filters";
}

/** Data exists, but the current search/filters exclude everything. */
export function CatalogNoResults({ onReset, reason }: CatalogNoResultsProps): React.JSX.Element {
  const isSearch = reason === "search";
  return (
    <EmptyState
      icon={isSearch ? <SearchX aria-hidden="true" /> : <Frown aria-hidden="true" />}
      title={isSearch ? "Ничего не найдено" : "Нет подходящих фестивалей"}
      description={
        isSearch
          ? "Попробуйте изменить запрос или сбросить фильтры."
          : "Под выбранные фильтры ничего не подходит. Попробуйте ослабить условия."
      }
      action={
        <Button variant="outline" onClick={onReset} leftIcon={<RotateCcw aria-hidden="true" />}>
          Сбросить фильтры
        </Button>
      }
    />
  );
}

interface CatalogErrorProps {
  onRetry: () => void;
  retrying?: boolean;
}

/** Load failed — offer a retry. */
export function CatalogError({ onRetry, retrying = false }: CatalogErrorProps): React.JSX.Element {
  return (
    <EmptyState
      icon={<Frown aria-hidden="true" />}
      title="Не удалось загрузить фестивали"
      description="Что-то пошло не так при загрузке каталога. Проверьте соединение и попробуйте снова."
      action={
        <Button onClick={onRetry} loading={retrying} leftIcon={<RotateCcw aria-hidden="true" />}>
          Повторить
        </Button>
      }
    />
  );
}
