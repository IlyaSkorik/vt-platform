import { z } from "zod";

/**
 * Client-side validation for the Authentication flows.
 *
 * These mirror the Identity contract (API-001 §4) so the UI catches obvious
 * mistakes before a round-trip, while the server stays authoritative — it may
 * still reject a syntactically valid password as breached/weak (`422`), which
 * the forms surface via Problem Details. Messages are ru-RU (primary locale,
 * ARCH-001 §8.6).
 */

/** Minimum password length per the platform password policy (ARCH-001 §11.2). */
export const PASSWORD_MIN_LENGTH = 12;

export const emailSchema = z.string().min(1, "Укажите email").email("Введите корректный email");

/**
 * Password policy: length + character-class variety. The server enforces the
 * authoritative policy (including breach checks); this is a fast local guard.
 */
export const passwordSchema = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Пароль должен содержать не менее ${PASSWORD_MIN_LENGTH} символов`)
  .regex(/[a-zа-яё]/, "Добавьте строчную букву")
  .regex(/[A-ZА-ЯЁ]/, "Добавьте заглавную букву")
  .regex(/\d/, "Добавьте цифру");

/** Login accepts any non-empty password — policy is only enforced on set. */
const loginPasswordSchema = z.string().min(1, "Укажите пароль");

const tokenSchema = z.string().min(1, "Токен отсутствует или недействителен");

export const loginSchema = z.object({
  email: emailSchema,
  password: loginPasswordSchema,
});
export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    firstName: z.string().min(1, "Укажите имя").max(100, "Имя не должно превышать 100 символов"),
    lastName: z
      .string()
      .min(1, "Укажите фамилию")
      .max(100, "Фамилия не должна превышать 100 символов"),
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Повторите пароль"),
    // Accepting the agreement is what creates the account, and what the account's data is
    // processed to perform (LEGAL-001 §4.4) — so it is required, and it is the only thing
    // required. No consent is asked for here: one that had to be given for registration to
    // work would not be freely given (LEGAL-001 §13.1, §13.2).
    acceptTerms: z.literal(true, {
      message:
        "Необходимо принять Пользовательское соглашение и подтвердить ознакомление с политикой",
    }),
    /** Optional by law and by design: refusing it changes nothing else. */
    acceptMarketing: z.boolean(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
  });
export type RegisterValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: emailSchema,
});
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    token: tokenSchema,
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Повторите пароль"),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
  });
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;
