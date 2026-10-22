import { CircleCheck, CircleX } from "lucide-react";
import { useEffect } from "react";
import { Link, useSearchParams } from "react-router";
import { useVerifyEmail } from "@/features/auth";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import { readPostAuthRedirect } from "@/shared/lib";
import { Alert, Button, LoadingState } from "@/shared/ui";

/**
 * Email-verification screen — a total state machine over one route.
 *
 * The token from the emailed link (`?token=`) is confirmed once
 * (`POST /auth/email-verification/confirmations`) and every outcome maps to a
 * single terminal screen, so the page can NEVER stay in the loading state:
 *
 *   - no token           → invalid-link screen;
 *   - 200                → verified;
 *   - 409 (conflict)     → already verified (verification IS the desired state,
 *                          so this is a success-equivalent terminal state — not
 *                          a failure);
 *   - 410 (gone)         → link expired, offer to resend;
 *   - 422                → invalid token;
 *   - network (status 0) → connectivity error, offer retry;
 *   - 5xx                → server error, offer retry;
 *   - other 4xx          → generic failure.
 *
 * Dispatch is driven off the mutation's own `isIdle` state rather than a ref
 * guard. Under `StrictMode` React mounts → unmounts → remounts; a ref guard set
 * on the throwaway mount would block the *retained* mount forever (its mutation
 * would stay idle → infinite spinner). Firing while `isIdle` makes the retained
 * observer always dispatch; a duplicate dispatch is harmless because 409 (the
 * only outcome a second confirmation produces) is treated as success.
 */
export function VerifyEmailPage(): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const verifyEmail = useVerifyEmail();
  const { mutate, status } = verifyEmail;

  useEffect(() => {
    if (token && status === "idle") {
      mutate(token);
    }
  }, [token, status, mutate]);

  const outcome = resolveOutcome(token, verifyEmail.status, verifyEmail.error);

  if (outcome === "loading") {
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

  return <VerificationResult {...RESULTS[outcome]} />;
}

/** The terminal outcomes the page can render (loading is transient, not terminal). */
type Outcome =
  | "loading"
  | "verified"
  | "already-verified"
  | "expired"
  | "invalid-token"
  | "missing-token"
  | "network-error"
  | "server-error"
  | "failed";

/**
 * Map the (token, mutation status, error) triple to exactly one outcome. Total
 * by construction: every status and every error status has a branch, so there
 * is no input for which the page lacks a terminal screen.
 */
function resolveOutcome(
  token: string | null,
  status: "idle" | "pending" | "success" | "error",
  error: ApiError | null,
): Outcome {
  if (!token) {
    return "missing-token";
  }
  if (status === "success") {
    return "verified";
  }
  if (status === "error") {
    const httpStatus = error instanceof ApiError ? error.status : undefined;
    switch (httpStatus) {
      case 409:
        return "already-verified";
      case 410:
        return "expired";
      case 422:
        return "invalid-token";
      case 0:
        return "network-error";
      default:
        return httpStatus !== undefined && httpStatus >= 500 ? "server-error" : "failed";
    }
  }
  // idle (about to dispatch) or pending (in flight).
  return "loading";
}

interface VerificationResultProps {
  variant: "success" | "failed";
  title: string;
  message: string;
  action: { kind: "login" } | { kind: "resend" } | { kind: "retry" };
}

/** Static presentation for each terminal outcome. */
const RESULTS: Record<Exclude<Outcome, "loading">, VerificationResultProps> = {
  verified: {
    variant: "success",
    title: "Email подтверждён",
    message: "Ваш адрес электронной почты успешно подтверждён. Теперь вы можете войти в аккаунт.",
    action: { kind: "login" },
  },
  "already-verified": {
    variant: "success",
    title: "Email уже подтверждён",
    message: "Этот адрес электронной почты уже был подтверждён ранее. Вы можете войти в аккаунт.",
    action: { kind: "login" },
  },
  expired: {
    variant: "failed",
    title: "Срок действия ссылки истёк",
    message:
      "Ссылка подтверждения устарела. Войдите в аккаунт, чтобы запросить новое письмо с подтверждением.",
    action: { kind: "resend" },
  },
  "invalid-token": {
    variant: "failed",
    title: "Не удалось подтвердить email",
    message: "Ссылка недействительна. Откройте письмо ещё раз и перейдите по полной ссылке.",
    action: { kind: "login" },
  },
  "missing-token": {
    variant: "failed",
    title: "Ссылка недействительна",
    message:
      "В ссылке отсутствует токен подтверждения. Откройте письмо ещё раз и перейдите по полной ссылке.",
    action: { kind: "login" },
  },
  "network-error": {
    variant: "failed",
    title: "Нет соединения",
    message:
      "Не удалось связаться с сервером. Проверьте подключение к интернету и попробуйте снова.",
    action: { kind: "retry" },
  },
  "server-error": {
    variant: "failed",
    title: "Ошибка сервера",
    message: "На сервере произошла ошибка. Попробуйте повторить попытку через несколько минут.",
    action: { kind: "retry" },
  },
  failed: {
    variant: "failed",
    title: "Не удалось подтвердить email",
    message: "Ссылка недействительна или уже была использована. Попробуйте войти в аккаунт.",
    action: { kind: "login" },
  },
};

/** Terminal presentation for a verification outcome (success / failed + action). */
function VerificationResult({
  variant,
  title,
  message,
  action,
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
      <OutcomeAction action={action} />
    </section>
  );
}

/**
 * The single call-to-action for a terminal screen. "resend" and "retry" both
 * route to login: the resend endpoint requires an authenticated session, and a
 * retry of a failed confirmation starts from a fresh sign-in.
 *
 * The sign-in link carries whatever the account was on its way to before it had to
 * register — a jury invitation, usually. This is the far end of the detour described
 * in `post-auth-redirect`, and the last screen that can keep it from being lost.
 */
function OutcomeAction({
  action,
}: {
  action: VerificationResultProps["action"];
}): React.JSX.Element {
  const parked = readPostAuthRedirect();
  const loginPath =
    parked == null ? ROUTES.login : `${ROUTES.login}?next=${encodeURIComponent(parked)}`;
  if (action.kind === "retry") {
    return (
      <Button asChild className="w-full">
        <Link to={loginPath} reloadDocument>
          Повторить попытку
        </Link>
      </Button>
    );
  }
  const label = action.kind === "resend" ? "Отправить письмо повторно" : "Перейти ко входу";
  return (
    <Button asChild className="w-full">
      <Link to={loginPath}>{label}</Link>
    </Button>
  );
}
