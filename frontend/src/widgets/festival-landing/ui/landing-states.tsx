import { ArrowLeft, Frown, MapPinOff, RotateCcw } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button, EmptyState } from "@/shared/ui";

function BackToCatalog(): React.JSX.Element {
  return (
    <Button asChild variant="outline" leftIcon={<ArrowLeft aria-hidden="true" />}>
      <Link to={ROUTES.cabinetCompetitions}>К каталогу</Link>
    </Button>
  );
}

/** The competition does not exist or is not publicly available (404). */
export function LandingNotFound(): React.JSX.Element {
  return (
    <EmptyState
      icon={<MapPinOff aria-hidden="true" />}
      title="Фестиваль не найден"
      description="Возможно, страница ещё не опубликована организатором или была снята с публикации. Проверьте ссылку или вернитесь в каталог."
      action={<BackToCatalog />}
    />
  );
}

interface LandingErrorProps {
  onRetry: () => void;
  retrying?: boolean;
}

/** Load failed for a reason other than 404 — offer a retry. */
export function LandingError({ onRetry, retrying = false }: LandingErrorProps): React.JSX.Element {
  return (
    <EmptyState
      icon={<Frown aria-hidden="true" />}
      title="Не удалось загрузить страницу фестиваля"
      description="Что-то пошло не так при загрузке. Проверьте соединение и попробуйте снова."
      action={
        <div className="flex flex-wrap justify-center gap-2">
          <Button onClick={onRetry} loading={retrying} leftIcon={<RotateCcw aria-hidden="true" />}>
            Повторить
          </Button>
          <BackToCatalog />
        </div>
      }
    />
  );
}
