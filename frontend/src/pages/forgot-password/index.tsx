import { Link } from "react-router";
import { ROUTES } from "@/shared/config";

/**
 * Password-recovery screen (placeholder).
 *
 * Bootstrap scope: heading and navigation only. The reset request flow
 * (`POST /auth/password-reset/requests`, API-001 §4.7) is delivered by the
 * Auth feature.
 */
export function ForgotPasswordPage(): React.JSX.Element {
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Восстановление пароля</h1>
        <p className="text-muted-foreground text-sm">
          Укажите email — мы отправим ссылку для сброса пароля.
        </p>
      </header>

      <div className="rounded-md border border-dashed p-4 text-muted-foreground text-sm">
        Форма восстановления появится здесь.
      </div>

      <footer className="text-muted-foreground text-sm">
        <Link to={ROUTES.login} className="text-primary hover:underline">
          Вернуться ко входу
        </Link>
      </footer>
    </section>
  );
}
