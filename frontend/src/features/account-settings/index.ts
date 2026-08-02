/**
 * Public API of the `account-settings` feature.
 *
 * What a signed-in person may change about their own account: the password, the
 * email address, the phone number, and how the interface looks. Each card is a
 * self-contained form over one `PUT /users/me/*` sub-resource; the page supplies
 * the account and re-reads it when something changes.
 */
export { useChangeEmail, useChangePassword, useChangePhone } from "./api/hooks";
export { normalizePhone } from "./model/schemas";
export {
  AppearanceCard,
  type AppearanceCardProps,
  type ThemePreference,
} from "./ui/appearance-card";
export { EmailCard, type EmailCardProps } from "./ui/email-card";
export { PasswordCard } from "./ui/password-card";
export { PhoneCard, type PhoneCardProps } from "./ui/phone-card";
