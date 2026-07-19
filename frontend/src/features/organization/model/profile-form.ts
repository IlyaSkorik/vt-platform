import { z } from "zod";
import type { OrganizationProfile, OrganizationProfileUpdate } from "../api/profile";

/**
 * The editable slice of the organization profile — the identity fields (name,
 * slug) are shown read-only, so the form owns only the contact & legal details.
 */
const SHORT_MAX = 200;
const ADDRESS_MAX = 500;
const LEGAL_MAX = 5000;

/**
 * A free-text field: trimmed and length-bounded, blank allowed. Kept a required
 * `string` (empty when unset) rather than optional so the form value type stays
 * a plain `string` under `exactOptionalPropertyTypes` — the profile mapper and
 * RHF `register` always supply a string, so "optional" would only add friction.
 */
const optionalText = (max: number) => z.string().trim().max(max, `Не более ${max} символов`);

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const URL_RE = /^https?:\/\/.+/i;

export const organizationProfileSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Укажите название организации")
    .max(SHORT_MAX, `Не более ${SHORT_MAX} символов`),
  phone: optionalText(SHORT_MAX),
  email: optionalText(SHORT_MAX).refine((value) => value === "" || EMAIL_RE.test(value), {
    message: "Введите корректный email",
  }),
  website: optionalText(SHORT_MAX).refine((value) => value === "" || URL_RE.test(value), {
    message: "Введите корректный URL (http:// или https://)",
  }),
  address: optionalText(ADDRESS_MAX),
  vk: optionalText(SHORT_MAX),
  instagram: optionalText(SHORT_MAX),
  telegram: optionalText(SHORT_MAX),
  legalInformation: optionalText(LEGAL_MAX),
});

export type OrganizationProfileFormValues = z.infer<typeof organizationProfileSchema>;

/** The set of field names the form owns — used to map server field errors. */
export const ORGANIZATION_PROFILE_FIELDS = [
  "name",
  "phone",
  "email",
  "website",
  "address",
  "vk",
  "instagram",
  "telegram",
  "legalInformation",
] as const;

/** Seed the form from the fetched profile (nulls become empty strings). */
export function profileToFormValues(profile: OrganizationProfile): OrganizationProfileFormValues {
  return {
    name: profile.name,
    phone: profile.phone ?? "",
    email: profile.email ?? "",
    website: profile.website ?? "",
    address: profile.address ?? "",
    vk: profile.vk ?? "",
    instagram: profile.instagram ?? "",
    telegram: profile.telegram ?? "",
    legalInformation: profile.legalInformation ?? "",
  };
}

/** Turn form values into a PATCH payload (empty strings become null to clear). */
export function formValuesToUpdate(
  values: OrganizationProfileFormValues,
): OrganizationProfileUpdate {
  const clean = (value: string): string | null => {
    const trimmed = value.trim();
    return trimmed === "" ? null : trimmed;
  };
  return {
    name: values.name.trim(),
    phone: clean(values.phone),
    email: clean(values.email),
    website: clean(values.website),
    address: clean(values.address),
    vk: clean(values.vk),
    instagram: clean(values.instagram),
    telegram: clean(values.telegram),
    legalInformation: clean(values.legalInformation),
  };
}
