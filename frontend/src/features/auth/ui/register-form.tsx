import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { ACCOUNT_CONSENTS, ConsentCheckbox, type ConsentDefinition } from "@/shared/consents";
import { formatPersonName } from "@/shared/lib";
import { Alert, Button, Input, PasswordInput } from "@/shared/ui";
import { useRegister } from "../api";
import { applyProblemToForm } from "../lib/problem-to-form";
import { type RegisterValues, registerSchema } from "../model/schemas";
import { PasswordRequirements, passwordFieldError } from "./password-requirements";

/** The catalogue entry for a code, or a loud failure — a missing consent must not ship. */
function accountConsent(code: string): ConsentDefinition {
  const consent = ACCOUNT_CONSENTS.find((candidate) => candidate.code === code);
  if (consent == null) {
    throw new Error(`Missing consent definition for "${code}".`);
  }
  return consent;
}

const TERMS_CONSENT = accountConsent("terms_of_service");
const MARKETING_CONSENT = accountConsent("marketing");

interface RegisterFormProps {
  /** Called with the registered email after the account is created. */
  onSuccess: (email: string) => void;
}

/**
 * Registration form — `POST /auth/registration`.
 *
 * Enforces the client password policy and confirmation locally, records acceptance of the
 * Пользовательское соглашение (the contract the account rests on) plus the newsletter
 * consent nobody has to give, and maps server field errors (e.g. email already in use
 * `409`, weak password `422`) back onto the offending field. New-password fields hint
 * `new-password` for password managers.
 */
export function RegisterForm({ onSuccess }: RegisterFormProps): React.JSX.Element {
  const registerAccount = useRegister();
  const [formError, setFormError] = useState<string | null>(null);
  const alertId = useId();
  const requirementsId = useId();

  const {
    register,
    handleSubmit,
    getValues,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false as unknown as true,
      acceptMarketing: false,
    },
  });

  const acceptTerms = watch("acceptTerms");
  const acceptMarketing = watch("acceptMarketing");
  const password = watch("password");

  /**
   * Registers a name field, tidying its capitalisation once the user leaves it.
   *
   * The account holder's name is printed back at them across the cabinet, so
   * "ИВАНОВ" typed with caps lock on is worth fixing at the point of entry. On
   * blur rather than on every keystroke, so the value never shifts mid-word.
   */
  const registerName = (field: "firstName" | "lastName") =>
    register(field, {
      onBlur: () => {
        const current = getValues(field);
        const formatted = formatPersonName(current);
        if (formatted !== current) {
          setValue(field, formatted, { shouldValidate: true });
        }
      },
    });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await registerAccount.mutateAsync(values);
      onSuccess(values.email);
    } catch (error) {
      setFormError(
        applyProblemToForm<RegisterValues>(error, {
          setError,
          knownFields: ["firstName", "lastName", "email", "password", "confirmPassword"],
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
        label="Имя"
        autoComplete="given-name"
        autoFocus
        error={errors.firstName?.message}
        {...registerName("firstName")}
      />

      <Input
        label="Фамилия"
        autoComplete="family-name"
        error={errors.lastName?.message}
        {...registerName("lastName")}
      />

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />

      {/* The policy is shown as a checklist that ticks itself off, not as a sentence to
          audit your own typing against — the field and the list are one control, hence
          the shared spacing and the `aria-describedby` tying them together. */}
      <div className="space-y-2">
        <PasswordInput
          label="Пароль"
          autoComplete="new-password"
          aria-describedby={requirementsId}
          error={passwordFieldError(errors.password)}
          {...register("password")}
        />
        <PasswordRequirements
          id={requirementsId}
          value={password}
          invalid={errors.password != null}
        />
      </div>

      <PasswordInput
        label="Подтверждение пароля"
        autoComplete="new-password"
        error={errors.confirmPassword?.message}
        {...register("confirmPassword")}
      />

      {/* Two boxes, and they are different in kind: the first accepts the agreement the
          account exists under, the second is the newsletter consent nobody has to want.
          Both take their wording and version from the catalogue that also supplies what
          gets recorded, so the journal names the text that was actually shown. */}
      <div className="space-y-3">
        <ConsentCheckbox
          consent={TERMS_CONSENT}
          checked={acceptTerms === true}
          error={errors.acceptTerms?.message}
          onChange={(checked) => setValue("acceptTerms", checked as true, { shouldValidate: true })}
        />
        <ConsentCheckbox
          consent={MARKETING_CONSENT}
          checked={acceptMarketing === true}
          onChange={(checked) => setValue("acceptMarketing", checked, { shouldValidate: true })}
        />
      </div>

      <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
        Зарегистрироваться
      </Button>
    </form>
  );
}
