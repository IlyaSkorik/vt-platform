import { Link } from "react-router";
import { ROUTES } from "@/shared/config";

/**
 * Email-verification screen (placeholder).
 *
 * Bootstrap scope: heading and navigation only. Token confirmation
 * (`POST /auth/email-verification/confirmations`, API-001 §4.2) is delivered
 * by the Auth feature.
 */
export function VerifyEmailPage(): React.JSX.Element {
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Подтверждение email</h1>
        <p className="text-muted-foreground text-sm">Мы проверяем вашу ссылку подтверждения.</p>
      </header>

      <div className="rounded-md border border-dashed p-4 text-muted-foreground text-sm">
        Статус подтверждения появится здесь.
      </div>

      <footer className="text-muted-foreground text-sm">
        <Link to={ROUTES.login} className="text-primary hover:underline">
          Перейти ко входу
        </Link>
      </footer>
    </section>
  );
}
