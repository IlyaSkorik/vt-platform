import { ShieldX } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Alert, Button } from "@/shared/ui";

/**
 * Unauthorized (403) screen.
 *
 * Shown when an authenticated user lacks the role/scope for a resource
 * (deny-by-default RBAC, API-000 §18). It confirms the account is signed in but
 * not permitted — never leaking whether the resource exists (API-000 §26).
 */
export function UnauthorizedPage(): React.JSX.Element {
  return (
    <section className="space-y-6 text-center">
      <p className="font-mono text-muted-foreground text-sm">403</p>
      <div className="flex justify-center text-danger" aria-hidden="true">
        <ShieldX className="size-12" />
      </div>
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Доступ запрещён</h1>
      </header>
      <Alert variant="danger" role="status">
        У вашего аккаунта нет прав для просмотра этой страницы. Если вы считаете, что это ошибка,
        обратитесь к администратору.
      </Alert>
      <div className="flex flex-col gap-2">
        <Button asChild className="w-full">
          <Link to={ROUTES.cabinet}>На главную страницу кабинета</Link>
        </Button>
        <Button asChild variant="ghost" className="w-full">
          <Link to={ROUTES.home}>На главную</Link>
        </Button>
      </div>
    </section>
  );
}
