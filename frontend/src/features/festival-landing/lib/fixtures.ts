import type { FestivalContacts, FestivalDetail, LandingBlock } from "./types";

/**
 * Test factory for a landing {@link LandingBlock}. Only used by unit tests;
 * tree-shaken out of the production bundle.
 */
export function makeBlock(overrides: Partial<LandingBlock> = {}): LandingBlock {
  return {
    id: "block-1",
    type: "CONTENT",
    sortOrder: 0,
    title: null,
    subtitle: null,
    coverImage: null,
    body: null,
    contentFormat: null,
    jury: [],
    partners: [],
    images: [],
    faq: [],
    ...overrides,
  };
}

/** Test factory for the reused Competition Contacts projection. */
export function makeContacts(overrides: Partial<FestivalContacts> = {}): FestivalContacts {
  return {
    organizationName: "Оргкомитет фестиваля",
    phone: "+375 29 123-45-67",
    email: "hello@fest.by",
    website: "https://fest.by",
    address: "г. Минск, пр. Независимости, 1",
    social: { vk: "https://vk.com/fest", telegram: null, instagram: null },
    team: [],
    emergency: { phone: null, email: null, notes: null },
    venue: {
      name: "Дворец культуры",
      address: "пр. Независимости, 1",
      city: "Минск",
      country: "Беларусь",
      googleMapsUrl: "https://maps.google.com/?q=fest",
      yandexMapsUrl: null,
      directions: null,
    },
    ...overrides,
  };
}

/**
 * Test factory for a {@link FestivalDetail}. Overrides are shallow-merged;
 * `pricing`, `landing` and `contacts` merge one level deep.
 */
export function makeFestivalDetail(overrides: Partial<FestivalDetail> = {}): FestivalDetail {
  const { pricing, landing, contacts, ...rest } = overrides;
  return {
    id: "01900000-0000-7000-8000-000000000001",
    title: "Весенний вокальный фестиваль",
    season: "2025/2026",
    description: "Описание фестиваля",
    status: "REGISTRATION_OPEN",
    organizer: { id: "org-1", name: "Дом талантов", logo: null },
    city: "Минск",
    venueName: "Дворец культуры",
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
    createdAt: "2026-05-01T10:00:00Z",
    updatedAt: "2026-05-01T10:00:00Z",
    regulation: {
      title: "Положение фестиваля 2026",
      version: "v1",
      publicationDate: "2026-05-15",
      fileReference: "/media/regulations/fest.pdf",
    },
    documents: [
      {
        id: "doc-1",
        title: "Программа фестиваля",
        category: "PROGRAM",
        description: "Расписание по дням",
        fileReference: "/media/documents/program.pdf",
      },
    ],
    ...rest,
    pricing: { amountFrom: "30.00", currency: "BYN", multiple: true, ...pricing },
    landing: {
      blocks: [
        makeBlock({ id: "hero", type: "HERO", sortOrder: 0, title: "Взлёт талантов" }),
        makeBlock({ id: "regulation", type: "REGULATION", sortOrder: 1 }),
        makeBlock({ id: "documents", type: "DOCUMENTS", sortOrder: 2 }),
        makeBlock({
          id: "about",
          type: "CONTENT",
          sortOrder: 3,
          title: "О фестивале",
          body: "Ежегодный праздник детского творчества.",
          contentFormat: "PLAIN",
        }),
        makeBlock({ id: "venue", type: "VENUE", sortOrder: 4 }),
      ],
      ...landing,
    },
    contacts: contacts ? makeContacts(contacts) : makeContacts(),
  };
}
