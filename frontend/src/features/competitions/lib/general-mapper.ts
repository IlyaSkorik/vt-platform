import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import type { GeneralInformationValues } from "../model/schemas";

const CONTACT_TYPES = ["VK", "INSTAGRAM", "TELEGRAM"] as const;

type ContactField = "vk" | "instagram" | "telegram";

const CONTACT_FIELD_MAP: Record<ContactField, (typeof CONTACT_TYPES)[number]> = {
  vk: "VK",
  instagram: "INSTAGRAM",
  telegram: "TELEGRAM",
};

export function competitionToGeneralValues(
  competition: CompetitionDetail,
): GeneralInformationValues {
  const contactValue = (type: string): string =>
    competition.contacts.find((contact) => contact.type === type)?.value ?? "";

  return {
    title: competition.title,
    season: competition.season,
    description: competition.description ?? "",
    poster: competition.branding.poster ?? "",
    venueName: competition.venue?.name ?? "",
    venueAddress: competition.venue?.address ?? "",
    registrationStart: competition.registrationPeriod?.start ?? "",
    registrationEnd: competition.registrationPeriod?.end ?? "",
    competitionStart: competition.competitionPeriod?.start ?? "",
    competitionEnd: competition.competitionPeriod?.end ?? "",
    vk: contactValue("VK"),
    instagram: contactValue("INSTAGRAM"),
    telegram: contactValue("TELEGRAM"),
  };
}

export function generalValuesToPayload(values: GeneralInformationValues) {
  return {
    title: values.title,
    season: values.season,
    description: values.description?.trim() ? values.description.trim() : null,
    logo: null,
    banner: null,
    venueName: values.venueName?.trim() ? values.venueName.trim() : null,
    venueAddress: values.venueAddress?.trim() ? values.venueAddress.trim() : null,
    registrationStart: values.registrationStart || null,
    registrationEnd: values.registrationEnd || null,
    competitionStart: values.competitionStart || null,
    competitionEnd: values.competitionEnd || null,
  };
}

export function brandingValuesToPayload(values: GeneralInformationValues) {
  return {
    logo: null,
    banner: null,
    poster: values.poster?.trim() ? values.poster.trim() : null,
  };
}

export function contactSyncTargets(
  competition: CompetitionDetail,
  values: GeneralInformationValues,
): Array<{
  field: ContactField;
  contactType: string;
  value: string;
  existingContactId?: string;
}> {
  return (Object.keys(CONTACT_FIELD_MAP) as ContactField[]).map((field) => {
    const contactType = CONTACT_FIELD_MAP[field];
    const existing = competition.contacts.find((contact) => contact.type === contactType);
    const target: {
      field: ContactField;
      contactType: string;
      value: string;
      existingContactId?: string;
    } = {
      field,
      contactType,
      value: values[field] ?? "",
    };
    if (existing?.id) {
      target.existingContactId = existing.id;
    }
    return target;
  });
}
