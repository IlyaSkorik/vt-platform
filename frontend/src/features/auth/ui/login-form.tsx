import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { Alert, Button, Checkbox, Input, PasswordInput } from "@/shared/ui";
import { useLogin } from "../api";
import { applyProblemToForm } from "../lib/problem-to-form";
import { type LoginValues, loginSchema } from "../model/schemas";

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
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  const rememberMe = watch("rememberMe");

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login.mutateAsync(values);
      onSuccess();
    } catch (error) {
      setFormError(
        applyProblemToForm<LoginValues>(error, {
          setError,
          knownFields: ["email", "password"],
        }),
      );
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
      {formError ? (
        <Alert id={alertId} variant="danger" title="Не удалось войти" role="alert">
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

      <PasswordInput
        label="Пароль"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />

      <Checkbox
        label="Запомнить меня"
        checked={rememberMe}
        onCheckedChange={(checked) => setValue("rememberMe", checked === true)}
      />

      <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
        Войти
      </Button>
    </form>
  );
}
