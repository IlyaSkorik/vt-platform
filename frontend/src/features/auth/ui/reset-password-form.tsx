import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { Alert, Button, PasswordInput } from "@/shared/ui";
import { useResetPassword } from "../api";
import { applyProblemToForm } from "../lib/problem-to-form";
import {
  PASSWORD_MIN_LENGTH,
  type ResetPasswordValues,
  resetPasswordSchema,
} from "../model/schemas";

interface ResetPasswordFormProps {
  /** The reset token from the emailed link (`?token=`). */
  token: string;
  /** Called after the password is reset, so the page can route to login. */
  onSuccess: () => void;
}

/**
 * Reset-password form — `POST /auth/password-reset/confirmations`.
 *
 * Sets a new password using the emailed token (carried as a hidden field). An
 * expired token (`410`) or weak/breached password (`422`) surfaces via Problem
 * Details; on success all sessions are revoked and the page routes to login.
 */
export function ResetPasswordForm({ token, onSuccess }: ResetPasswordFormProps): React.JSX.Element {
  const resetPassword = useResetPassword();
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token, password: "", confirmPassword: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await resetPassword.mutateAsync(values);
      onSuccess();
    } catch (error) {
      setFormError(
        applyProblemToForm<ResetPasswordValues>(error, {
          setError,
          knownFields: ["password", "confirmPassword", "token"],
        }),
      );
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
      {formError ? (
        <Alert id={alertId} variant="danger" title="Не удалось сбросить пароль" role="alert">
          {formError}
        </Alert>
      ) : null}

      <input type="hidden" {...register("token")} />

      <PasswordInput
        label="Новый пароль"
        autoComplete="new-password"
        autoFocus
        description={`Минимум ${PASSWORD_MIN_LENGTH} символов, буквы разного регистра и цифра.`}
        error={errors.password?.message}
        {...register("password")}
      />

      <PasswordInput
        label="Подтверждение пароля"
        autoComplete="new-password"
        error={errors.confirmPassword?.message}
        {...register("confirmPassword")}
      />

      <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
        Сохранить пароль
      </Button>
    </form>
  );
}
