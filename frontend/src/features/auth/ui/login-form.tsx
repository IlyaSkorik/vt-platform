import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { ApiError } from "@/shared/api";
import { Alert, Button, Input, PasswordInput } from "@/shared/ui";
import { useLogin, useResendVerification } from "../api";
import { applyProblemToForm, formLevelMessage } from "../lib/problem-to-form";
import { type LoginValues, loginSchema } from "../model/schemas";

/**
 * Problem `type` suffix the edge returns when sign-in is refused because the
 * account's email is unconfirmed (IDN-001). Keyed off the stable `type` URI —
 * never the human `detail` — so the copy stays owned by the client.
 */
const EMAIL_NOT_VERIFIED_TYPE = "email-not-verified";

/** True when the login failure is specifically an unverified-email refusal. */
function isEmailNotVerified(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.problem?.type?.endsWith(EMAIL_NOT_VERIFIED_TYPE) ?? false)
  );
}

interface LoginFormProps {
  /** Called after a session is established, so the page can navigate. */
  onSuccess: () => void;
}

/**
 * Login form — credentials → `POST /auth/sessions`.
 *
 * React Hook Form + Zod for validation; submit is disabled while the request
 * is in flight; server rejections (bad credentials, suspended account, rate
 * limit) render as a form-level Alert via Problem Details. All controls come
 * from the UI kit and carry autocomplete hints for password managers.
 */
export function LoginForm({ onSuccess }: LoginFormProps): React.JSX.Element {
  const login = useLogin();
  const resend = useResendVerification();
  const [formError, setFormError] = useState<string | null>(null);
  // Set to the submitted address when login is refused as unverified — enables the
  // inline "resend the confirmation link" action. `resent` flips after a resend.
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);
  const [resent, setResent] = useState(false);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const resetFeedback = (): void => {
    setFormError(null);
    setUnverifiedEmail(null);
    setResent(false);
  };

  const onSubmit = handleSubmit(async (values) => {
    resetFeedback();
    try {
      await login.mutateAsync(values);
      onSuccess();
    } catch (error) {
      if (isEmailNotVerified(error)) {
        setFormError(
          "Подтвердите email, чтобы войти. Мы отправили ссылку на вашу почту при регистрации — проверьте входящие и папку «Спам».",
        );
        setUnverifiedEmail(values.email);
        return;
      }
      setFormError(
        applyProblemToForm<LoginValues>(error, {
          setError,
          knownFields: ["email", "password"],
        }),
      );
    }
  });

  const onResend = async (): Promise<void> => {
    if (!unverifiedEmail) {
      return;
    }
    try {
      await resend.mutateAsync(unverifiedEmail);
      setResent(true);
    } catch (error) {
      setFormError(formLevelMessage(error));
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
      {formError ? (
        <Alert id={alertId} variant="danger" title="Не удалось войти" role="alert">
          {formError}
          {unverifiedEmail ? (
            <div className="mt-3">
              {resent ? (
                <p className="text-sm">Письмо отправлено на {unverifiedEmail}. Проверьте почту.</p>
              ) : (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  loading={resend.isPending}
                  disabled={resend.isPending}
                  onClick={onResend}
                >
                  Выслать письмо повторно
                </Button>
              )}
            </div>
          ) : null}
        </Alert>
      ) : null}

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        autoFocus
        error={errors.email?.message}
        {...register("email")}
      />

      <PasswordInput
        label="Пароль"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />

      <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
        Войти
      </Button>
    </form>
  );
}
