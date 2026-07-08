import { Link, useLocation, useNavigate } from "react-router";
import { useAuth } from "@/app/providers";
import { LoginForm } from "@/features/auth";
import { ROUTES } from "@/shared/config";

interface LocationState {
  from?: { pathname?: string };
}

/**
 * Login screen.
 *
 * On success it re-derives the session (`GET /users/me`) and returns the user
 * to the page they originally attempted (preserved by `ProtectedRoute`), or the
 * dashboard by default.
 */
export function LoginPage(): React.JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const { refresh } = useAuth();

  const state = location.state as LocationState | null;
  const from = state?.from?.pathname ?? ROUTES.dashboard;

  const handleSuccess = async (): Promise<void> => {
    await refresh();
    navigate(from, { replace: true });
  };

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Вход</h1>
        <p className="text-muted-foreground text-sm">Войдите в свой аккаунт, чтобы продолжить.</p>
      </header>

      <LoginForm onSuccess={handleSuccess} />

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
