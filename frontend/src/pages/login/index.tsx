import { Link, useLocation, useNavigate } from "react-router";
import { useAuth } from "@/app/providers";
import { LoginForm } from "@/features/auth";
import { ROUTES } from "@/shared/config";
import { authPathWithNext, clearPostAuthRedirect, readPostAuthRedirect } from "@/shared/lib";

interface LocationState {
  from?: { pathname?: string; search?: string };
}

function safeNext(value: string | null): string | null {
  if (value == null || !value.startsWith("/") || value.startsWith("//")) {
    return null;
  }
  return value;
}

/**
 * Login screen.
 *
 * On success it re-derives the session (`GET /users/me`) and returns the user
 * to the page they originally attempted (preserved by `ProtectedRoute`), or the
 * personal cabinet by default. Login never routes to a staff-only surface.
 */
export function LoginPage(): React.JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const { refresh } = useAuth();

  const state = location.state as LocationState | null;
  const params = new URLSearchParams(location.search);
  const stateFrom =
    state?.from?.pathname != null ? `${state.from.pathname}${state.from.search ?? ""}` : null;
  // The parked destination is the last resort and the one that survives registration:
  // somebody invited onto a jury signs up, confirms their address from a second e-mail,
  // and arrives here with no `?next=` left anywhere. See `post-auth-redirect`.
  const from =
    safeNext(params.get("next")) ?? safeNext(stateFrom) ?? readPostAuthRedirect() ?? ROUTES.cabinet;

  const handleSuccess = async (): Promise<void> => {
    await refresh();
    clearPostAuthRedirect();
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
          <Link
            to={authPathWithNext(ROUTES.register, from === ROUTES.cabinet ? null : from)}
            className="text-primary hover:underline"
          >
            Зарегистрироваться
          </Link>
        </span>
      </footer>
    </section>
  );
}
