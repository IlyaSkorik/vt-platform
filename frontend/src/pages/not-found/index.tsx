import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

/**
 * 404 page — rendered for any unmatched route.
 */
export function NotFoundPage(): React.JSX.Element {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="font-mono text-muted-foreground text-sm">404</p>
      <div className="space-y-2">
        <h1 className="font-bold text-3xl tracking-tight">Страница не найдена</h1>
        <p className="max-w-md text-muted-foreground text-sm">
          Возможно, ссылка устарела или страница была перемещена.
        </p>
      </div>
      <Button asChild>
        <Link to={ROUTES.home}>На главную</Link>
      </Button>
    </div>
  );
}
