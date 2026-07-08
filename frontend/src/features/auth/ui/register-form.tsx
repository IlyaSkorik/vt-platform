import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Alert, Button, Checkbox, Input, PasswordInput } from "@/shared/ui";
import { useRegister } from "../api";
import { applyProblemToForm } from "../lib/problem-to-form";
import { PASSWORD_MIN_LENGTH, type RegisterValues, registerSchema } from "../model/schemas";

interface RegisterFormProps {
  /** Called with the registered email after the account is created. */
  onSuccess: (email: string) => void;
}

/**
 * Registration form — `POST /auth/registration`.
 *
 * Enforces the client password policy and confirmation locally, requires terms
 * acceptance (IDN-010), and maps server field errors (e.g. email already in
 * use `409`, weak password `422`) back onto the offending field. New-password
 * fields hint `new-password` for password managers.
 */
export function RegisterForm({ onSuccess }: RegisterFormProps): React.JSX.Element {
  const registerAccount = useRegister();
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      displayName: "",
      email: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false as unknown as true,
    },
  });

  const acceptTerms = watch("acceptTerms");

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await registerAccount.mutateAsync(values);
      onSuccess(values.email);
    } catch (error) {
      setFormError(
        applyProblemToForm<RegisterValues>(error, {
          setError,
          knownFields: ["displayName", "email", "password", "confirmPassword"],
        }),
      );
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
      {formError ? (
        <Alert id={alertId} variant="danger" title="Не удалось зарегистрироваться" role="alert">
          {formError}
        </Alert>
      ) : null}

      <Input
        label="Отображаемое имя"
        autoComplete="name"
        autoFocus
        error={errors.displayName?.message}
        {...register("displayName")}
      />

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />

      <PasswordInput
        label="Пароль"
        autoComplete="new-password"
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

      <Checkbox
        label={
          <span>
            Я принимаю{" "}
            <Link to={ROUTES.home} className="text-primary hover:underline">
              условия использования
            </Link>
          </span>
        }
        checked={acceptTerms === true}
        error={errors.acceptTerms?.message}
        onCheckedChange={(checked) =>
          setValue("acceptTerms", (checked === true) as true, { shouldValidate: true })
        }
      />

      <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
        Зарегистрироваться
      </Button>
    </form>
  );
}
