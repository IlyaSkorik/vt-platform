import { z } from "zod";

import { emailSchema, passwordSchema } from "@/features/auth";

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
 * A phone number in the shape the backend's value object accepts: E.164, so a
 * leading ``+`` and 10–15 digits. Everything else a person might type — spaces,
 * brackets, dashes, a Russian leading ``8`` — is normalized before it gets here.
 */
export const changePhoneSchema = z.object({
  phone: z
    .string()
    .min(1, "Укажите номер телефона")
    .regex(/^\+\d{10,15}$/, "Введите номер в международном формате, например +79991234567"),
});
export type ChangePhoneValues = z.infer<typeof changePhoneSchema>;

/**
 * Turn what a person typed into what the API takes.
 *
 * Russian numbers are habitually written starting with ``8``; the same number in
 * E.164 starts ``+7``. Rejecting that as malformed would be pedantry about a
 * convention the whole country uses, so it is translated instead.
 */
export function normalizePhone(input: string): string {
  const digits = input.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("8")) {
    return `+7${digits.slice(1)}`;
  }
  return digits ? `+${digits}` : "";
}
