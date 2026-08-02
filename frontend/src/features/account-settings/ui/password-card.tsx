import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";

import { applyProblemToForm, PASSWORD_MIN_LENGTH } from "@/features/auth";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  PasswordInput,
  toast,
} from "@/shared/ui";

import { useChangePassword } from "../api/hooks";
import { type ChangePasswordValues, changePasswordSchema } from "../model/schemas";

/**
 * Change the account's password.
 *
 * The current password is asked for and sent: the server refuses the change
 * without it, so a session left open on a shared computer cannot be turned into
 * a lockout. The session survives — this is not the emailed reset, and there is
 * no reason to sign somebody out of a task they are in the middle of.
 */
export function PasswordCard(): React.JSX.Element {
  const changePassword = useChangePassword();
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await changePassword.mutateAsync({
        currentPassword: values.currentPassword,
        newPassword: values.newPassword,
      });
      reset();
      toast.success("Пароль изменён");
    } catch (error) {
      setFormError(
        applyProblemToForm<ChangePasswordValues>(error, {
          setError,
          // `/password` is the pointer the server uses for a weak new password.
          knownFields: ["currentPassword", "newPassword", "confirmPassword"],
        }),
      );
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="size-4 text-muted-foreground" aria-hidden="true" />
          Пароль
        </CardTitle>
        <CardDescription>
          Смена пароля не завершает текущий сеанс — вы останетесь в кабинете.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
          {formError ? (
            <Alert id={alertId} variant="danger" title="Не удалось изменить пароль" role="alert">
              {formError}
            </Alert>
          ) : null}

          <PasswordInput
            label="Текущий пароль"
            autoComplete="current-password"
            error={errors.currentPassword?.message}
            {...register("currentPassword")}
          />
          <PasswordInput
            label="Новый пароль"
            autoComplete="new-password"
            description={`Минимум ${PASSWORD_MIN_LENGTH} символов, буквы разного регистра и цифра.`}
            error={errors.newPassword?.message}
            {...register("newPassword")}
          />
          <PasswordInput
            label="Повторите новый пароль"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register("confirmPassword")}
          />

          <Button type="submit" loading={isSubmitting} disabled={isSubmitting}>
            Сохранить пароль
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
