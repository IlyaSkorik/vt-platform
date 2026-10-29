import type { Festival } from "./types";

/**
 * Test factory for a {@link Festival}. Only used by unit tests; tree-shaken out
 * of the production bundle. Overrides are shallow-merged; `pricing` merges too.
 */
export function makeFestival(overrides: Partial<Festival> = {}): Festival {
  const { pricing, ...rest } = overrides;
  return {
    id: "01900000-0000-7000-8000-000000000001",
    slug: "vesenniy-festival-2025-2026",
    title: "Весенний фестиваль",
    season: "2025/2026",
    description: "Описание фестиваля",
    status: "REGISTRATION_OPEN",
    organizer: { id: "org-1", name: "Дом талантов", logo: null },
    city: "Минск",
    venueName: "Минск",
    venueAddress: "пр. Независимости, 1",
    coverImage: null,
    competitionStart: "2026-08-01",
    competitionEnd: "2026-08-03",
    registrationStart: "2026-06-01",
    registrationEnd: "2026-07-20",
    applicationDeadline: null,
    modes: ["IN_PERSON"],
    formats: [{ name: "Очно", mode: "IN_PERSON" }],
    categories: ["Вокал"],
    ageMin: 7,
    ageMax: 18,
    createdAt: "2026-05-01T10:00:00Z",
    updatedAt: "2026-05-01T10:00:00Z",
    ...rest,
    pricing: { amountFrom: "30.00", currency: "BYN", multiple: false, ...pricing },
  };
}
