import { MailCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { ForgotPasswordForm } from "@/features/auth";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

/**
 * Password-recovery screen.
 *
 * The request always succeeds server-side (`202`) to avoid revealing account
 * existence (API-000 §26), so the confirmation is deliberately neutral: "if an
 * account exists, we've sent a link" — regardless of whether the email matched.
 */
export function ForgotPasswordPage(): React.JSX.Element {
  const [sent, setSent] = useState(false);

  if (sent) {
    return (
      <section className="space-y-6 text-center">
        <div className="flex justify-center text-success" aria-hidden="true">
          <MailCheck className="size-12" />
        </div>
        <header className="space-y-1">
          <h1 className="font-semibold text-xl tracking-tight">Письмо отправлено</h1>
          <p className="text-muted-foreground text-sm">
            Если аккаунт с таким email существует, мы отправили ссылку для сброса пароля. Проверьте
            почту, включая папку «Спам».
          </p>
        </header>
        <Button asChild variant="outline" className="w-full">
          <Link to={ROUTES.login}>Вернуться ко входу</Link>
        </Button>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">Восстановление пароля</h1>
        <p className="text-muted-foreground text-sm">
          Укажите email — мы отправим ссылку для сброса пароля.
        </p>
      </header>

      <ForgotPasswordForm onSuccess={() => setSent(true)} />

      <footer className="text-center text-muted-foreground text-sm">
        <Link to={ROUTES.login} className="text-primary hover:underline">
          Вернуться ко входу
        </Link>
      </footer>
    </section>
  );
}
