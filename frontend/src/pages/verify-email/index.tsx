import { CircleCheck, CircleX } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router";
import { useVerifyEmail } from "@/features/auth";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import { Alert, Button, LoadingState } from "@/shared/ui";

/**
 * Email-verification screen — three states in one route:
 *   - verifying: token present, confirmation in flight (spinner);
 *   - success:   the email was verified;
 *   - failed:    no token, an expired token (`410`), or an invalid one (`422`).
 *
 * The token from the emailed link (`?token=`) is confirmed once on mount
 * (`POST /auth/email-verification/confirmations`). A `StrictMode` double-invoke
 * guard keeps the mutation to a single call.
 */
export function VerifyEmailPage(): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const verifyEmail = useVerifyEmail();
  const startedRef = useRef(false);

  useEffect(() => {
    if (!token || startedRef.current) {
      return;
    }
    startedRef.current = true;
    verifyEmail.mutate(token);
  }, [token, verifyEmail]);

  if (!token) {
    return (
      <VerificationResult
        variant="failed"
        title="Ссылка недействительна"
        message="В ссылке отсутствует токен подтверждения. Откройте письмо ещё раз и перейдите по полной ссылке."
      />
    );
  }

  if (verifyEmail.isPending || verifyEmail.isIdle) {
    return (
      <section className="space-y-6 text-center">
        <header className="space-y-1">
          <h1 className="font-semibold text-xl tracking-tight">Подтверждение email</h1>
        </header>
        <div className="flex justify-center py-4">
          <LoadingState size="lg" label="Проверяем вашу ссылку…" />
        </div>
      </section>
    );
  }

  if (verifyEmail.isSuccess) {
    return (
      <VerificationResult
        variant="success"
        title="Email подтверждён"
        message="Ваш адрес электронной почты успешно подтверждён. Теперь вы можете войти в аккаунт."
      />
    );
  }

  const expired = verifyEmail.error instanceof ApiError && verifyEmail.error.status === 410;
  return (
    <VerificationResult
      variant="failed"
      title={expired ? "Срок действия ссылки истёк" : "Не удалось подтвердить email"}
      message={
        expired
          ? "Ссылка подтверждения устарела. Запросите новое письмо после входа в аккаунт."
          : "Ссылка недействительна или уже была использована. Попробуйте войти или запросить новое письмо."
      }
    />
  );
}

interface VerificationResultProps {
  variant: "success" | "failed";
  title: string;
  message: string;
}

/** Terminal presentation for the verification outcome (success / failed). */
function VerificationResult({
  variant,
  title,
  message,
}: VerificationResultProps): React.JSX.Element {
  const isSuccess = variant === "success";
  return (
    <section className="space-y-6 text-center">
      <div
        className={
          isSuccess ? "flex justify-center text-success" : "flex justify-center text-danger"
        }
        aria-hidden="true"
      >
        {isSuccess ? <CircleCheck className="size-12" /> : <CircleX className="size-12" />}
      </div>
      <header className="space-y-1">
        <h1 className="font-semibold text-xl tracking-tight">{title}</h1>
      </header>
      <Alert variant={isSuccess ? "success" : "danger"} role="status">
        {message}
      </Alert>
      <Button asChild className="w-full">
        <Link to={ROUTES.login}>Перейти ко входу</Link>
      </Button>
    </section>
  );
}
