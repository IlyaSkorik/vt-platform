import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ResetPasswordForm } from "@/features/auth";
import { ROUTES } from "@/shared/config";
import { Alert, toast } from "@/shared/ui";

/**
 * Reset-password screen.
 *
 * Reads the reset token from the emailed link (`?token=`). A missing token is a
 * broken/expired link, so the form is not shown — the user is pointed back to
 * "forgot password". On success all sessions are revoked (API-001 §4.7) and the
 * screen routes to login with a confirmation toast.
 */
export function ResetPasswordPage(): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";
  const [done, setDone] = useState(false);

  const handleSuccess = (): void => {
    setDone(true);
    toast.success("Пароль изменён. Войдите с новым паролем.");
    navigate(ROUTES.login, { replace: true });
  };

  if (!token) {
    return (
      <section className="space-y-6">
        <header className="space-y-1">
          <h1 className="font-semibold text-xl tracking-tight">Ссылка недействительна</h1>
        </header>
        <Alert variant="danger" title="Токен отсутствует">
          Ссылка для сброса пароля некорректна или устарела. Запросите новую.
        </Alert>
        <footer className="text-center text-muted-foreground text-sm">
          <Link to={ROUTES.forgotPassword} className="text-primary hover:underline">
            Запросить новую ссылку
          </Link>
        </footer>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Новый пароль</h1>
        <p className="text-muted-foreground text-sm">
          Придумайте новый пароль для вашего аккаунта.
        </p>
      </header>

      <ResetPasswordForm token={token} onSuccess={handleSuccess} />

      {done ? null : (
        <footer className="text-center text-muted-foreground text-sm">
          <Link to={ROUTES.login} className="text-primary hover:underline">
            Вернуться ко входу
          </Link>
        </footer>
      )}
    </section>
  );
}
