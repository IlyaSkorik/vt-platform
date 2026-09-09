import { emailSchema, passwordSchema } from "@/features/auth";
import { z } from "@/shared/lib/zod";

/**
 * Client-side validation for the account's own settings.
 *
 * The same rule as everywhere else in this codebase: a fast local guard so an
 * obvious mistake costs no round-trip, with the server staying authoritative —
 * it alone knows whether the current password is right, whether an address is
 * already taken, and whether a password has been seen in a breach.
 */

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Введите текущий пароль"),
    newPassword: passwordSchema,
    confirmPassword: z.string().min(1, "Повторите новый пароль"),
  })
  .refine((values) => values.newPassword === values.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
  })
  .refine((values) => values.newPassword !== values.currentPassword, {
    message: "Новый пароль совпадает с текущим",
    path: ["newPassword"],
  });
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

export const changeEmailSchema = z.object({
  email: emailSchema,
  currentPassword: z.string().min(1, "Введите пароль, чтобы подтвердить смену адреса"),
});
export type ChangeEmailValues = z.infer<typeof changeEmailSchema>;

/**
 * A Belarusian number, in the shape the backend's value object accepts.
 *
 * ``+375`` and nine national digits — the only calling code the platform serves,
 * because that is where its festivals are held and where an organizer dials on the
 * day. Everything else a person might type (spaces, brackets, dashes, a leading
 * ``8`` or ``0``) is normalized before it gets here.
 */
export const changePhoneSchema = z.object({
  phone: z
    .string()
    .min(1, "Укажите номер телефона")
    .regex(/^\+375\d{9}$/, "Введите белорусский номер, например +375 29 123-45-67"),
});
export type ChangePhoneValues = z.infer<typeof changePhoneSchema>;

/**
 * Turn what a person typed into what the API takes.
 *
 * Belarusian numbers are written several ways and all of them are the same number:
 * ``+375 29 123-45-67`` in full, ``8 029 123-45-67`` when dialling within the
 * country, ``029 123-45-67`` locally, and just ``29 123-45-67`` when the operator
 * code is understood. Refusing any of those as malformed would be pedantry about
 * conventions the whole country uses, so they are translated instead.
 *
 * Anything that is not one of those shapes is returned with a bare ``+`` and left
 * for the schema to refuse — guessing at a number nobody can dial is worse than
 * saying it is wrong.
 */
export function normalizePhone(input: string): string {
  const digits = input.replace(/\D/g, "");
  // Already international, with or without the domestic trunk prefix in front.
  if (digits.length === 12 && digits.startsWith("375")) {
    return `+${digits}`;
  }
  if (digits.length === 13 && digits.startsWith("8375")) {
    return `+${digits.slice(1)}`;
  }
  // Domestic: 8 + 0 + code + number, or 0 + code + number, or the bare nine.
  if (digits.length === 11 && digits.startsWith("80")) {
    return `+375${digits.slice(2)}`;
  }
  if (digits.length === 10 && digits.startsWith("0")) {
    return `+375${digits.slice(1)}`;
  }
  if (digits.length === 9) {
    return `+375${digits}`;
  }
  return digits ? `+${digits}` : "";
}
