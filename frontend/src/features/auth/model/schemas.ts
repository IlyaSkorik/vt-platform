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

/** Upper bound the server's `PasswordPolicy` rejects past (IDN-003). */
export const PASSWORD_MAX_LENGTH = 128;

export const emailSchema = z.string().min(1, "Укажите email").email("Введите корректный email");

/**
 * One requirement of the password policy, in a form both the validator and the
 * UI can read.
 *
 * The policy used to live twice over: once as regexes inside
 * {@link passwordSchema} and once as a sentence under the password field. The two
 * had already drifted — the sentence promised a special symbol the schema never
 * asked for, so the only way to learn about that rule was a `422` from the
 * server. Stating each rule once, with the predicate that decides it, is what
 * lets the field show a live checklist that cannot disagree with what will
 * actually be accepted.
 *
 * Predicates mirror the server's `PasswordPolicy` character classes exactly,
 * including its alphabet: a password is built from printable ASCII only. A
 * Cyrillic password is a password its owner cannot type on a keyboard laid out
 * for another language, and one whose bytes depend on which normalisation form
 * the client happened to send — so "буква" here always means a Latin letter.
 */
export interface PasswordRule {
  /** Stable key for lists and tests. */
  id: string;
  /** Checklist wording: the requirement itself, in the affirmative. */
  label: string;
  /** Field-error wording: what to do about it, when it is not met. */
  message: string;
  isSatisfied: (password: string) => boolean;
}

/** The platform password policy, in the order a person builds a password. */
export const PASSWORD_RULES = [
  {
    id: "length",
    label: `Не менее ${PASSWORD_MIN_LENGTH} символов`,
    message: `Пароль должен содержать не менее ${PASSWORD_MIN_LENGTH} символов`,
    isSatisfied: (password) => password.length >= PASSWORD_MIN_LENGTH,
  },
  {
    id: "lowercase",
    label: "Строчная латинская буква (a–z)",
    message: "Добавьте строчную латинскую букву",
    isSatisfied: (password) => /[a-z]/.test(password),
  },
  {
    id: "uppercase",
    label: "Заглавная латинская буква (A–Z)",
    message: "Добавьте заглавную латинскую букву",
    isSatisfied: (password) => /[A-Z]/.test(password),
  },
  {
    id: "digit",
    label: "Цифра (0–9)",
    message: "Добавьте цифру",
    isSatisfied: (password) => /[0-9]/.test(password),
  },
  {
    id: "symbol",
    label: "Специальный символ (например ! ? @ #)",
    message: "Добавьте специальный символ, например ! ? @ #",
    // Printable ASCII that is neither a Latin letter nor a digit — spelled out as
    // ranges rather than "anything non-alphanumeric", which a Cyrillic letter
    // would also satisfy while failing the alphabet rule below.
    isSatisfied: (password) => /[\x20-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]/.test(password),
  },
] as const satisfies readonly PasswordRule[];

/** Printable ASCII: Latin letters, digits, spaces and the ASCII specials. */
const PASSWORD_ALPHABET = /^[\x20-\x7E]*$/;

/**
 * Said on the field rather than as a checklist row.
 *
 * Every other rule is something to add, and a row that reads "no Cyrillic" would
 * be ticked green over an empty field — satisfied by having typed nothing. This
 * one is something to remove, so it is named where a mistake is named.
 */
export const PASSWORD_ALPHABET_MESSAGE =
  "Используйте только латинские буквы, цифры и специальные символы";

/**
 * Password policy: length + character-class variety, assembled from
 * {@link PASSWORD_RULES}. The server enforces the authoritative policy
 * (including breach checks); this is a fast local guard.
 *
 * Every unmet rule is reported, not just the first, matching the server's
 * `PasswordValidationResult` — the checklist under the field is what renders
 * them all, and the field itself shows whichever comes first.
 */
export const passwordSchema = PASSWORD_RULES.reduce<z.ZodString>(
  (schema, rule) => schema.refine(rule.isSatisfied, rule.message),
  z
    .string()
    .max(PASSWORD_MAX_LENGTH, `Пароль не должен превышать ${PASSWORD_MAX_LENGTH} символов`)
    // Before the character classes, so a Cyrillic password is told what is wrong with
    // it — the classes would otherwise report four separate absences instead.
    .refine((password) => PASSWORD_ALPHABET.test(password), PASSWORD_ALPHABET_MESSAGE),
);

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
      message: "Необходимо принять Пользовательское соглашение",
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
