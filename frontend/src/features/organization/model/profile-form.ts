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

/**
 * The nine "with the support of" fields, flat and prefixed.
 *
 * Flat rather than a nested `supporter` object so every field keeps a plain
 * `errors.supporterPhone?.message` path, the same as the organizer's own fields
 * beside it; the mapper below is what turns them into the nested block the API
 * takes. `supporterName` is what makes the block exist, so it is the only one the
 * cross-field check below cares about.
 */
const SUPPORTER_FIELD_KEYS = [
  "supporterPhone",
  "supporterEmail",
  "supporterWebsite",
  "supporterAddress",
  "supporterVk",
  "supporterInstagram",
  "supporterTelegram",
  "supporterLegalInformation",
] as const;

const organizationProfileFields = z.object({
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
  supporterName: optionalText(SHORT_MAX),
  supporterPhone: optionalText(SHORT_MAX),
  supporterEmail: optionalText(SHORT_MAX).refine((value) => value === "" || EMAIL_RE.test(value), {
    message: "Введите корректный email",
  }),
  supporterWebsite: optionalText(SHORT_MAX).refine((value) => value === "" || URL_RE.test(value), {
    message: "Введите корректный URL (http:// или https://)",
  }),
  supporterAddress: optionalText(ADDRESS_MAX),
  supporterVk: optionalText(SHORT_MAX),
  supporterInstagram: optionalText(SHORT_MAX),
  supporterTelegram: optionalText(SHORT_MAX),
  supporterLegalInformation: optionalText(LEGAL_MAX),
});

/**
 * The profile form, plus the one rule that spans two fields.
 *
 * Filling in a supporting entity's details but not its name loses the whole block:
 * the name is what makes it exist, so the backend drops the rest with it. That is
 * the right storage rule and the wrong thing to do silently to someone who just
 * typed an address, so it is caught here and pointed at the name.
 */
export const organizationProfileSchema = organizationProfileFields.check((ctx) => {
  const values = ctx.value;
  if (values.supporterName !== "") {
    return;
  }
  if (SUPPORTER_FIELD_KEYS.some((key) => values[key] !== "")) {
    ctx.issues.push({
      code: "custom",
      input: values.supporterName,
      path: ["supporterName"],
      message: "Укажите название организации — иначе эти данные не сохранятся",
    });
  }
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
  "supporterName",
  ...SUPPORTER_FIELD_KEYS,
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
    // A profile with no supporting entity seeds every field blank, which is also
    // what the form submits back — so "no block" survives a save untouched.
    supporterName: profile.supporter?.name ?? "",
    supporterPhone: profile.supporter?.phone ?? "",
    supporterEmail: profile.supporter?.email ?? "",
    supporterWebsite: profile.supporter?.website ?? "",
    supporterAddress: profile.supporter?.address ?? "",
    supporterVk: profile.supporter?.vk ?? "",
    supporterInstagram: profile.supporter?.instagram ?? "",
    supporterTelegram: profile.supporter?.telegram ?? "",
    supporterLegalInformation: profile.supporter?.legalInformation ?? "",
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
    supporter: {
      // Sent even when blank: a blank name is the request to clear the block, and
      // omitting it would read as "leave whatever is stored" instead.
      name: values.supporterName.trim(),
      phone: clean(values.supporterPhone),
      email: clean(values.supporterEmail),
      website: clean(values.supporterWebsite),
      address: clean(values.supporterAddress),
      vk: clean(values.supporterVk),
      instagram: clean(values.supporterInstagram),
      telegram: clean(values.supporterTelegram),
      legalInformation: clean(values.supporterLegalInformation),
    },
  };
}
