import { describe, expect, it } from "vitest";
import {
  applyCatalog,
  deriveFilterOptions,
  filterFestivals,
  hasActiveFilters,
  searchFestivals,
  sortFestivals,
} from "./filter-festivals";
import { makeFestival } from "./fixtures";
import { EMPTY_CATALOG_FILTERS } from "./types";

const NOW = new Date("2026-07-15T12:00:00Z");

describe("searchFestivals", () => {
  const festivals = [
    makeFestival({ id: "a", title: "Весенний вокал", city: "Минск", categories: ["Вокал"] }),
    makeFestival({
      id: "b",
      title: "Танцевальный кубок",
      city: "Гомель",
      organizer: { id: "o2", name: "Арт-центр", logo: null },
      categories: ["Хореография"],
    }),
  ];

  it("returns all festivals for an empty query", () => {
    expect(searchFestivals(festivals, "  ")).toHaveLength(2);
  });

  it("matches by title", () => {
    expect(searchFestivals(festivals, "вокал").map((f) => f.id)).toEqual(["a"]);
  });

  it("matches by city and organizer", () => {
    expect(searchFestivals(festivals, "гомель").map((f) => f.id)).toEqual(["b"]);
    expect(searchFestivals(festivals, "арт-центр").map((f) => f.id)).toEqual(["b"]);
  });

  it("requires every term to match (AND)", () => {
    expect(searchFestivals(festivals, "минск вокал").map((f) => f.id)).toEqual(["a"]);
    expect(searchFestivals(festivals, "минск танцевальный")).toHaveLength(0);
  });
});

describe("filterFestivals", () => {
  it("filters by registration state and closing-soon window", () => {
    const open = makeFestival({
      id: "open",
      status: "REGISTRATION_OPEN",
      registrationEnd: "2026-09-01",
    });
    const closingSoon = makeFestival({
      id: "soon",
      status: "REGISTRATION_OPEN",
      registrationEnd: "2026-07-18",
    });
    const closed = makeFestival({ id: "closed", status: "REGISTRATION_CLOSED" });
    const festivals = [open, closingSoon, closed];

    expect(
      filterFestivals(festivals, { ...EMPTY_CATALOG_FILTERS, registration: ["OPEN"] }, NOW).map(
        (f) => f.id,
      ),
    ).toEqual(["open", "soon"]);

    expect(
      filterFestivals(
        festivals,
        { ...EMPTY_CATALOG_FILTERS, registration: ["CLOSING_SOON"] },
        NOW,
      ).map((f) => f.id),
    ).toEqual(["soon"]);
  });

  it("filters by mode (OR within the axis)", () => {
    const inPerson = makeFestival({ id: "ip", modes: ["IN_PERSON"] });
    const online = makeFestival({ id: "on", modes: ["ONLINE"] });
    const both = makeFestival({ id: "both", modes: ["IN_PERSON", "ONLINE"] });

    const result = filterFestivals(
      [inPerson, online, both],
      { ...EMPTY_CATALOG_FILTERS, modes: ["ONLINE"] },
      NOW,
    );
    expect(result.map((f) => f.id)).toEqual(["on", "both"]);
  });

  it("filters by city and category", () => {
    const a = makeFestival({ id: "a", city: "Минск", categories: ["Вокал"] });
    const b = makeFestival({ id: "b", city: "Брест", categories: ["Танцы"] });
    expect(
      filterFestivals([a, b], { ...EMPTY_CATALOG_FILTERS, cities: ["Брест"] }, NOW).map(
        (f) => f.id,
      ),
    ).toEqual(["b"]);
    expect(
      filterFestivals([a, b], { ...EMPTY_CATALOG_FILTERS, categories: ["Вокал"] }, NOW).map(
        (f) => f.id,
      ),
    ).toEqual(["a"]);
  });

  it("filters by competition date window (overlap)", () => {
    const august = makeFestival({
      id: "aug",
      competitionStart: "2026-08-01",
      competitionEnd: "2026-08-03",
    });
    const october = makeFestival({
      id: "oct",
      competitionStart: "2026-10-01",
      competitionEnd: "2026-10-02",
    });
    const result = filterFestivals(
      [august, october],
      { ...EMPTY_CATALOG_FILTERS, competitionFrom: "2026-09-01", competitionTo: null },
      NOW,
    );
    expect(result.map((f) => f.id)).toEqual(["oct"]);
  });
});

describe("sortFestivals", () => {
  const early = makeFestival({
    id: "early",
    title: "Ялта",
    createdAt: "2026-01-01T00:00:00Z",
    competitionStart: "2026-08-01",
    registrationEnd: "2026-07-01",
  });
  const late = makeFestival({
    id: "late",
    title: "Астрахань",
    createdAt: "2026-06-01T00:00:00Z",
    competitionStart: "2026-09-01",
    registrationEnd: "2026-08-15",
  });

  it("sorts newest first", () => {
    expect(sortFestivals([early, late], "NEWEST").map((f) => f.id)).toEqual(["late", "early"]);
  });

  it("sorts by closing soon (ascending cutoff)", () => {
    expect(sortFestivals([late, early], "CLOSING_SOON").map((f) => f.id)).toEqual([
      "early",
      "late",
    ]);
  });

  it("sorts by competition date", () => {
    expect(sortFestivals([late, early], "COMPETITION_DATE").map((f) => f.id)).toEqual([
      "early",
      "late",
    ]);
  });

  it("sorts alphabetically (ru locale)", () => {
    expect(sortFestivals([early, late], "ALPHABETICAL").map((f) => f.title)).toEqual([
      "Астрахань",
      "Ялта",
    ]);
  });

  it("does not mutate the input array", () => {
    const input = [early, late];
    sortFestivals(input, "ALPHABETICAL");
    expect(input.map((f) => f.id)).toEqual(["early", "late"]);
  });
});

describe("deriveFilterOptions", () => {
  it("collects unique cities and categories with counts", () => {
    const festivals = [
      makeFestival({ id: "a", city: "Минск", categories: ["Вокал", "Танцы"] }),
      makeFestival({ id: "b", city: "Минск", categories: ["Вокал"] }),
      makeFestival({ id: "c", city: null, categories: [] }),
    ];
    const options = deriveFilterOptions(festivals);
    expect(options.cities).toEqual([{ value: "Минск", count: 2 }]);
    expect(options.categories).toEqual([
      { value: "Вокал", count: 2 },
      { value: "Танцы", count: 1 },
    ]);
  });
});

describe("applyCatalog + hasActiveFilters", () => {
  it("runs search, filter and sort together", () => {
    const festivals = [
      makeFestival({ id: "a", title: "Вокал", city: "Минск", createdAt: "2026-01-01T00:00:00Z" }),
      makeFestival({ id: "b", title: "Вокал", city: "Брест", createdAt: "2026-06-01T00:00:00Z" }),
      makeFestival({ id: "c", title: "Танцы", city: "Минск", categories: ["Танцы"] }),
    ];
    const result = applyCatalog(
      festivals,
      { query: "вокал", sort: "NEWEST", filters: EMPTY_CATALOG_FILTERS },
      NOW,
    );
    expect(result.map((f) => f.id)).toEqual(["b", "a"]);
  });

  it("detects active filters", () => {
    expect(hasActiveFilters(EMPTY_CATALOG_FILTERS)).toBe(false);
    expect(hasActiveFilters({ ...EMPTY_CATALOG_FILTERS, modes: ["ONLINE"] })).toBe(true);
  });
});
