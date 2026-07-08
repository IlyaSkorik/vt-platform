import { Link } from "react-router";
import { ROUTES } from "@/shared/config";

/**
 * Registration screen (placeholder).
 *
 * Bootstrap scope: heading and navigation only. Account creation
 * (`POST /auth/registration`, API-001 §4.1) is delivered by the Auth feature.
 */
export function RegisterPage(): React.JSX.Element {
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Регистрация</h1>
        <p className="text-muted-foreground text-sm">Создайте аккаунт, чтобы начать работу.</p>
      </header>

      <div className="rounded-md border border-dashed p-4 text-muted-foreground text-sm">
        Форма регистрации появится здесь.
      </div>

      <footer className="text-muted-foreground text-sm">
        Уже есть аккаунт?{" "}
        <Link to={ROUTES.login} className="text-primary hover:underline">
          Войти
        </Link>
      </footer>
    </section>
  );
}
