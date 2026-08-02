import { zodResolver } from "@hookform/resolvers/zod";
import { Phone } from "lucide-react";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";

import { applyProblemToForm } from "@/features/auth";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  toast,
} from "@/shared/ui";

import { useChangePhone } from "../api/hooks";
import { type ChangePhoneValues, changePhoneSchema, normalizePhone } from "../model/schemas";

export interface PhoneCardProps {
  /** The account's current number, or `null` when none has been given. */
  phone: string | null;
  /** Re-read the account after a change. */
  onChanged: () => Promise<void> | void;
}

/**
 * The phone number an organizer can reach the applicant on.
 *
 * No password is asked for, unlike the address: a phone is a way *to* the person,
 * not a way back into the account, and putting a credential prompt in front of it
 * would only stop people from keeping it current.
 */
export function PhoneCard({ phone, onChanged }: PhoneCardProps): React.JSX.Element {
  const changePhone = useChangePhone();
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();

  const {
    register,
    handleSubmit,
    setValue,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ChangePhoneValues>({
    resolver: zodResolver(changePhoneSchema),
    defaultValues: { phone: phone ?? "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await changePhone.mutateAsync({ phone: values.phone });
      await onChanged();
      toast.success("Телефон сохранён");
    } catch (error) {
      setFormError(
        applyProblemToForm<ChangePhoneValues>(error, { setError, knownFields: ["phone"] }),
      );
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Phone className="size-4 text-muted-foreground" aria-hidden="true" />
          Телефон
        </CardTitle>
        <CardDescription>
          По этому номеру организатор свяжется с вами в день фестиваля. Необязательно, но лучше
          указать.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={alertId}>
          {formError ? (
            <Alert id={alertId} variant="danger" title="Не удалось сохранить номер" role="alert">
              {formError}
            </Alert>
          ) : null}

          <Input
            label="Номер телефона"
            type="tel"
            autoComplete="tel"
            placeholder="+375 29 123-45-67"
            description="Белорусский номер. Можно ввести как 8 029…, 029… или просто 29… — приведём к +375 сами."
            error={errors.phone?.message}
            {...register("phone", {
              // Normalized on leaving the field rather than on every keystroke, so
              // the caret does not jump about while somebody is still typing.
              onBlur: (event: React.FocusEvent<HTMLInputElement>) => {
                const normalized = normalizePhone(event.target.value);
                if (normalized && normalized !== event.target.value) {
                  setValue("phone", normalized, { shouldValidate: true, shouldDirty: true });
                }
              },
            })}
          />

          <Button type="submit" loading={isSubmitting} disabled={isSubmitting || !isDirty}>
            {phone ? "Сохранить номер" : "Добавить номер"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
