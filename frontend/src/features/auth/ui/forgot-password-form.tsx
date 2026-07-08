import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { Alert, Button, Input } from "@/shared/ui";
import { useForgotPassword } from "../api";
import { formLevelMessage } from "../lib/problem-to-form";
import { type ForgotPasswordValues, forgotPasswordSchema } from "../model/schemas";

interface ForgotPasswordFormProps {
  /** Called once the request is accepted, so the page can show confirmation. */
  onSuccess: () => void;
}

/**
 * Forgot-password form — `POST /auth/password-reset/requests`.
 *
 * The server always accepts (`202`) to avoid revealing whether an account
 * exists, so success is not a signal about the email — the page shows a neutral
 * "if an account exists…" confirmation. Only transport/rate-limit failures
 * surface as an error.
 */
export function ForgotPasswordForm({ onSuccess }: ForgotPasswordFormProps): React.JSX.Element {
  const forgotPassword = useForgotPassword();
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await forgotPassword.mutateAsync(values);
      onSuccess();
    } catch (error) {
      setFormError(formLevelMessage(error));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
      {formError ? (
        <Alert id={alertId} variant="danger" title="Не удалось отправить письмо" role="alert">
          {formError}
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

      <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
        Отправить ссылку
      </Button>
    </form>
  );
}
