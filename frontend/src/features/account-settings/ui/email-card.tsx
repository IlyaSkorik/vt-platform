import { zodResolver } from "@hookform/resolvers/zod";
import { Mail } from "lucide-react";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";

import { applyProblemToForm, useResendVerification } from "@/features/auth";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  toast,
} from "@/shared/ui";

import { useChangeEmail } from "../api/hooks";
import { type ChangeEmailValues, changeEmailSchema } from "../model/schemas";

export interface EmailCardProps {
  /** The account's current address. */
  email: string;
  /** Whether that address has been confirmed. */
  verified: boolean;
  /** Re-read the account after a change — the whole shell displays it. */
  onChanged: () => Promise<void> | void;
}

/**
 * The account's email address: what it is, whether it is confirmed, and how to move it.
 *
 * Confirmation is surfaced here and nowhere else in the cabinet, because this is
 * the one screen where it can be acted on — an unconfirmed address is the reason
 * a later sign-in is refused, and the resend button is the fix.
 *
 * Changing it re-asks for the password: the address is how the account is
 * recovered, so moving it somewhere its owner cannot reach is exactly the damage
 * a borrowed browser could otherwise do.
 */
export function EmailCard({ email, verified, onChanged }: EmailCardProps): React.JSX.Element {
  const changeEmail = useChangeEmail();
  const resend = useResendVerification();
  const [formError, setFormError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangeEmailValues>({
    resolver: zodResolver(changeEmailSchema),
    defaultValues: { email: "", currentPassword: "" },
  });

  const stopEditing = () => {
    setEditing(false);
    setFormError(null);
    reset();
  };

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await changeEmail.mutateAsync(values);
      await onChanged();
      stopEditing();
      toast.success(`Адрес изменён. Письмо для подтверждения отправлено на ${values.email}`);
    } catch (error) {
      setFormError(
        applyProblemToForm<ChangeEmailValues>(error, {
          setError,
          knownFields: ["email", "currentPassword"],
        }),
      );
    }
  });

  const onResend = () => {
    resend.mutate(email, {
      onSuccess: () => toast.success("Письмо отправлено. Проверьте почту."),
      onError: () => toast.error("Не удалось отправить письмо"),
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="size-4 text-muted-foreground" aria-hidden="true" />
          Электронная почта
        </CardTitle>
        <CardDescription>
          Адрес, на который приходят письма о заявках и через который восстанавливается доступ.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="wrap-anywhere font-medium text-sm">{email || "—"}</span>
            <Badge variant={verified ? "success" : "warning"} size="sm">
              {verified ? "Подтверждён" : "Не подтверждён"}
            </Badge>
          </div>
          {editing ? null : (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              Изменить
            </Button>
          )}
        </div>

        {verified ? null : (
          <Alert variant="warning" title="Подтвердите адрес">
            <p>
              Пока адрес не подтверждён, войти в кабинет заново не получится. Мы отправили письмо со
              ссылкой — если оно не пришло, запросите новое.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              loading={resend.isPending}
              onClick={onResend}
            >
              Отправить письмо ещё раз
            </Button>
          </Alert>
        )}

        {editing ? (
          <form
            onSubmit={onSubmit}
            noValidate
            className="space-y-4 border-border border-t pt-4"
            aria-describedby={alertId}
          >
            {formError ? (
              <Alert id={alertId} variant="danger" title="Не удалось изменить адрес" role="alert">
                {formError}
              </Alert>
            ) : null}

            <Input
              label="Новый адрес"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <Input
              label="Текущий пароль"
              type="password"
              autoComplete="current-password"
              description="Нужен, чтобы адрес нельзя было сменить с чужого устройства."
              error={errors.currentPassword?.message}
              {...register("currentPassword")}
            />
            <div className="flex flex-wrap gap-2">
              <Button type="submit" loading={isSubmitting} disabled={isSubmitting}>
                Сохранить адрес
              </Button>
              <Button type="button" variant="ghost" onClick={stopEditing}>
                Отмена
              </Button>
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}
