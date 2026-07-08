import { Clock } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Alert, Button } from "@/shared/ui";

/**
 * Session-expired screen.
 *
 * Reached when a previously live session dropped — the access token expired and
 * the silent refresh failed (refresh cookie gone, or reuse detection revoked the
 * token family, API-001 §4.5). Distinct from a plain unauthenticated visit so
 * the user understands they were signed out rather than never signed in.
 */
export function SessionExpiredPage(): React.JSX.Element {
  return (
    <section className="space-y-6 text-center">
      <div className="flex justify-center text-warning" aria-hidden="true">
        <Clock className="size-12" />
      </div>
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Сессия завершена</h1>
      </header>
      <Alert variant="warning" role="status">
        Время сессии истекло или она была завершена в целях безопасности. Войдите снова, чтобы
        продолжить.
      </Alert>
      <Button asChild className="w-full">
        <Link to={ROUTES.login}>Войти снова</Link>
      </Button>
    </section>
  );
}
