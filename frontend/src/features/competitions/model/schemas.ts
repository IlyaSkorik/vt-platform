import { z } from "zod";

const optionalUrl = z
  .string()
  .trim()
  .refine((value) => value.length === 0 || /^https?:\/\/.+/i.test(value), {
    message: "Введите корректный URL (http:// или https://)",
  });

function isValidDateOrder(start: string | undefined, end: string | undefined): boolean {
  if (!start || !end) {
    return true;
  }
  return start <= end;
}

export const generalInformationSchema = z
  .object({
    title: z.string().trim().min(1, "Укажите название конкурса").max(200),
    season: z.string().trim().min(1, "Укажите сезон").max(50),
    description: z.string().trim().max(2000).optional(),
    poster: z.string().trim().max(1024).optional(),
    venueName: z.string().trim().max(200).optional(),
    venueAddress: z.string().trim().max(500).optional(),
    registrationStart: z.string().optional(),
    registrationEnd: z.string().optional(),
    competitionStart: z.string().optional(),
    competitionEnd: z.string().optional(),
    vk: optionalUrl.optional(),
    instagram: optionalUrl.optional(),
    telegram: optionalUrl.optional(),
  })
  .superRefine((values, context) => {
    if (!isValidDateOrder(values.registrationStart, values.registrationEnd)) {
      context.addIssue({
        code: "custom",
        path: ["registrationEnd"],
        message: "Дата окончания регистрации не может быть раньше начала",
      });
    }
    if (!isValidDateOrder(values.competitionStart, values.competitionEnd)) {
      context.addIssue({
        code: "custom",
        path: ["competitionEnd"],
        message: "Дата окончания конкурса не может быть раньше начала",
      });
    }
  });

export type GeneralInformationValues = z.infer<typeof generalInformationSchema>;

export const regulationDraftSchema = z.object({
  title: z.string().trim().min(1, "Укажите название положения").max(200),
  version: z.string().trim().min(1, "Укажите версию").max(50),
  publicationDate: z.string().min(1, "Укажите дату публикации"),
  fileReference: z.string().trim().min(1, "Загрузите PDF-файл положения").max(1024),
  changeNote: z.string().trim().max(500).optional(),
});

export type RegulationDraftValues = z.infer<typeof regulationDraftSchema>;
