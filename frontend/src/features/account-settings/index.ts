/**
 * Public API of the `account-settings` feature.
 *
 * What a signed-in person may change about their own account: the password, the
 * email address, the phone number, the consents given, and how the interface looks.
 * Each card is a
 * self-contained form over one `PUT /users/me/*` sub-resource; the page supplies
 * the account and re-reads it when something changes.
 */
export {
  type ConsentEntry,
  useChangeEmail,
  useChangePassword,
  useChangePhone,
  useConsents,
  useGrantConsent,
  useWithdrawConsent,
} from "./api/hooks";
export { normalizePhone } from "./model/schemas";
export {
  AppearanceCard,
  type AppearanceCardProps,
  type ThemePreference,
} from "./ui/appearance-card";
export { ConsentsCard } from "./ui/consents-card";
export { EmailCard, type EmailCardProps } from "./ui/email-card";
export { PasswordCard } from "./ui/password-card";
export { PhoneCard, type PhoneCardProps } from "./ui/phone-card";
