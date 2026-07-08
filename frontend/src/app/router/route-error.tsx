import { isRouteErrorResponse, Link, useRouteError } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

/**
 * Router-level error element.
 *
 * Rendered by React Router when a route (or its lazy import/loader) throws.
 * Distinguishes HTTP-style route errors (e.g. 404 responses) from unexpected
 * exceptions and always offers a route back home.
 */
export function RouteError(): React.JSX.Element {
  const error = useRouteError();

  const title = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : "Непредвиденная ошибка";

  const description = isRouteErrorResponse(error)
    ? "Запрошенная страница недоступна."
    : "Не удалось отобразить страницу. Попробуйте вернуться на главную.";

  return (
    <div
      role="alert"
      className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center"
    >
      <div className="space-y-2">
        <h1 className="font-semibold text-2xl tracking-tight">{title}</h1>
        <p className="max-w-md text-muted-foreground text-sm">{description}</p>
      </div>
      <Button asChild>
        <Link to={ROUTES.home}>На главную</Link>
      </Button>
    </div>
  );
}
