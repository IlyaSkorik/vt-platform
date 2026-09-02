/**
 * The schema.org graphs, and the one place they can disagree with the page.
 *
 * A festival that overrides its contacts is presented under the overridden name —
 * that is what its footer shows. Structured data naming the organization's profile
 * instead would put a different organizer in the search result than on the page it
 * links to, which is the kind of mismatch a validator cannot catch.
 */
import { describe, expect, it } from "vitest";

import { makeContacts, makeFestivalDetail } from "@/features/festival-landing/lib/fixtures";

import { festivalEventSchema } from "./structured-data";

function organizerOf(schema: Record<string, unknown>): Record<string, unknown> {
  return schema.organizer as Record<string, unknown>;
}

describe("festivalEventSchema", () => {
  it("names the organizer the festival overrode, not the organization's profile", () => {
    const festival = makeFestivalDetail();

    const schema = festivalEventSchema(festival, { path: "/festivals/spring" });

    expect(festival.organizer.name).toBe("Дом талантов");
    expect(organizerOf(schema).name).toBe("Оргкомитет фестиваля");
  });

  it("falls back to the organization's profile when nothing was overridden", () => {
    const festival = makeFestivalDetail({ contacts: makeContacts({ organizationName: null }) });

    const schema = festivalEventSchema(festival, { path: "/festivals/spring" });

    expect(organizerOf(schema).name).toBe("Дом талантов");
  });
});
