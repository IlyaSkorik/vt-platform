import { MailCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { RegisterForm } from "@/features/auth";
import { ROUTES } from "@/shared/config";
import { authPathWithNext, rememberPostAuthRedirect } from "@/shared/lib";
import { Alert, Button } from "@/shared/ui";

/**
 * Registration screen.
 *
 * After the account is created (`POST /auth/registration`) the API dispatches a
 * verification email (IDN-001). The page then swaps to a "check your inbox"
 * confirmation rather than navigating away, so the user knows the next step.
 *
 * `?next=` is carried through to the sign-in link and parked in storage besides: this
 * screen is the middle of a detour that goes out through one e-mail and comes back
 * through another, and whoever arrived here from a jury invitation has to end up back
 * at it rather than in the participant cabinet.
 */
export function RegisterPage(): React.JSX.Element {
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next");
  const loginPath = authPathWithNext(ROUTES.login, next);

  // The one screen where the chain breaks: from here the account leaves for a
  // verification e-mail and comes back through a link that carries no `?next=`. This is
  // the last chance to record where it was going.
  useEffect(() => {
    if (next != null) {
      rememberPostAuthRedirect(next);
    }
  }, [next]);

  if (registeredEmail) {
    return (
      <section className="space-y-6 text-center">
        <div className="flex justify-center text-success" aria-hidden="true">
          <MailCheck className="size-12" />
        </div>
        <header className="space-y-1">
          <h1 className="font-semibold text-xl tracking-tight">Проверьте почту</h1>
          <p className="text-muted-foreground text-sm">
            Мы отправили ссылку для подтверждения на <strong>{registeredEmail}</strong>. Перейдите
            по ней, чтобы активировать аккаунт.
          </p>
        </header>
        <Alert variant="info" title="Не пришло письмо?">
          Проверьте папку «Спам». Ссылка действительна ограниченное время.
        </Alert>
        <Button asChild variant="outline" className="w-full">
          <Link to={loginPath}>Перейти ко входу</Link>
        </Button>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Регистрация</h1>
        <p className="text-muted-foreground text-sm">Создайте аккаунт, чтобы начать работу.</p>
      </header>

      <RegisterForm onSuccess={setRegisteredEmail} />

      <footer className="text-center text-muted-foreground text-sm">
        Уже есть аккаунт?{" "}
        <Link to={loginPath} className="text-primary hover:underline">
          Войти
        </Link>
      </footer>
    </section>
  );
}
