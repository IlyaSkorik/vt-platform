import { Link } from "react-router";
import { ROUTES } from "@/shared/config";

/**
 * Login screen (placeholder).
 *
 * Bootstrap scope: heading and navigation only. The credential form
 * (React Hook Form + Zod) and session creation (`POST /auth/sessions`,
 * API-001 §4.4) are delivered by the Auth feature.
 */
export function LoginPage(): React.JSX.Element {
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Вход</h1>
        <p className="text-muted-foreground text-sm">Войдите в свой аккаунт, чтобы продолжить.</p>
      </header>

      <div className="rounded-md border border-dashed p-4 text-muted-foreground text-sm">
        Форма входа появится здесь.
      </div>

      <footer className="flex flex-col gap-2 text-muted-foreground text-sm">
        <Link to={ROUTES.forgotPassword} className="text-primary hover:underline">
          Забыли пароль?
        </Link>
        <span>
          Нет аккаунта?{" "}
          <Link to={ROUTES.register} className="text-primary hover:underline">
            Зарегистрироваться
          </Link>
        </span>
      </footer>
    </section>
  );
}
