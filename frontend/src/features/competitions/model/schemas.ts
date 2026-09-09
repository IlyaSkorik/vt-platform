import { z } from "@/shared/lib/zod";

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
    title: z.string().trim().min(1, "Укажите название фестиваля").max(200),
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
        message: "Дата окончания фестиваля не может быть раньше начала",
      });
    }
  });

export type GeneralInformationValues = z.infer<typeof generalInformationSchema>;

export const regulationDraftSchema = z.object({
  title: z.string().trim().min(1, "Укажите название положения").max(200),
  version: z.string().trim().min(1, "Укажите версию").max(50),
  publicationDate: z.string().min(1, "Укажите дату публикации"),
  fileReference: z.string().trim().min(1, "Загрузите PDF или укажите ссылку на документ").max(1024),
  changeNote: z.string().trim().max(500).optional(),
});

export type RegulationDraftValues = z.infer<typeof regulationDraftSchema>;

export const DOCUMENT_CATEGORIES = [
  "REGULATION",
  "PROGRAM",
  "SCHEDULE",
  "REQUISITES",
  "MEMO",
  "ACCOMMODATION",
  "OTHER",
] as const;

/** Categories selectable in the documents library (regulations live in their own section). */
export const DOCUMENT_FORM_CATEGORIES = [
  "PROGRAM",
  "SCHEDULE",
  "REQUISITES",
  "MEMO",
  "ACCOMMODATION",
  "OTHER",
] as const;

export const DOCUMENT_VISIBILITIES = ["ALL", "PUBLIC", "PARTICIPANTS", "STAFF"] as const;

export const documentFormSchema = z.object({
  title: z.string().trim().min(1, "Укажите название документа").max(200),
  description: z.string().trim().max(2000).optional(),
  category: z.enum(DOCUMENT_FORM_CATEGORIES, { message: "Выберите тип документа" }),
  visibility: z.enum(DOCUMENT_VISIBILITIES, { message: "Выберите видимость" }),
  fileReference: z.string().trim().min(1, "Загрузите файл документа").max(1024),
  sortOrder: z.number().int().min(0, "Порядок не может быть отрицательным"),
  published: z.boolean(),
});

export type DocumentFormValues = z.infer<typeof documentFormSchema>;
export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number];
export type DocumentFormCategory = (typeof DOCUMENT_FORM_CATEGORIES)[number];
