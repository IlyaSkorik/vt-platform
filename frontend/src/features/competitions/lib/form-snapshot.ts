import type { GeneralInformationValues } from "../model/schemas";

/** Stable serialization for dirty/autosave comparisons. */
export function generalFormSnapshot(values: GeneralInformationValues): string {
  return JSON.stringify({
    title: values.title.trim(),
    season: values.season.trim(),
    description: values.description?.trim() ?? "",
    poster: values.poster?.trim() ?? "",
    venueName: values.venueName?.trim() ?? "",
    venueAddress: values.venueAddress?.trim() ?? "",
    registrationStart: values.registrationStart ?? "",
    registrationEnd: values.registrationEnd ?? "",
    competitionStart: values.competitionStart ?? "",
    competitionEnd: values.competitionEnd ?? "",
    vk: values.vk?.trim() ?? "",
    instagram: values.instagram?.trim() ?? "",
    telegram: values.telegram?.trim() ?? "",
  });
}
