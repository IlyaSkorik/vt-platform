import { Medal } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button, EmptyState } from "@/shared/ui";

interface CompetitionsEmptyStateProps {
  onCreate: () => void;
  creating?: boolean;
}

export function CompetitionsEmptyState({
  onCreate,
  creating = false,
}: CompetitionsEmptyStateProps): React.JSX.Element {
  return (
    <EmptyState
      icon={<Medal aria-hidden="true" />}
      title="Пока нет фестивалей"
      description="Создайте первый фестиваль, чтобы настроить категории, цены и регистрацию."
      action={
        <Button onClick={onCreate} loading={creating} disabled={creating}>
          Создать фестиваль
        </Button>
      }
    />
  );
}

export function CompetitionsErrorState({ onRetry }: { onRetry: () => void }): React.JSX.Element {
  return (
    <EmptyState
      title="Не удалось загрузить фестивали"
      description="Проверьте соединение и попробуйте снова."
      action={
        <div className="flex flex-wrap gap-2">
          <Button onClick={onRetry}>Повторить</Button>
          <Button asChild variant="outline">
            <Link to={ROUTES.staff}>На дашборд</Link>
          </Button>
        </div>
      }
    />
  );
}
