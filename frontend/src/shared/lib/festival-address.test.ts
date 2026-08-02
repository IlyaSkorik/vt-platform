import { describe, expect, it } from "vitest";
import { festivalPath, festivalSegment } from "./festival-address";

describe("festivalSegment", () => {
  it("prefers the readable slug", () => {
    expect(festivalSegment({ id: "0190-uuid", slug: "vesenniy-vokal-2026" })).toBe(
      "vesenniy-vokal-2026",
    );
  });

  it("falls back to the id for a competition that has no slug", () => {
    // Rows predating slugs still have to be linkable — the id never stops resolving.
    expect(festivalSegment({ id: "0190-uuid", slug: null })).toBe("0190-uuid");
  });

  it("treats a blank slug as no slug", () => {
    // An empty segment would silently address the catalog instead of the festival.
    expect(festivalSegment({ id: "0190-uuid", slug: "   " })).toBe("0190-uuid");
  });

  it("does not require the field at all", () => {
    expect(festivalSegment({ id: "0190-uuid" })).toBe("0190-uuid");
  });
});

describe("festivalPath", () => {
  it("joins the segment onto the given base", () => {
    expect(festivalPath({ id: "x", slug: "gармония" }, "/competitions")).toBe(
      "/competitions/gармония",
    );
  });

  it("addresses the same competition identically wherever it is linked", () => {
    // The property that matters: two surfaces linking one festival must produce
    // one URL, or search sees two pages with the same content.
    const festival = { id: "0190-uuid", slug: "garmoniya-2026" };

    expect(festivalPath(festival, "/competitions")).toBe("/competitions/garmoniya-2026");
    expect(festivalPath(festival, "/cabinet/competitions")).toBe(
      "/cabinet/competitions/garmoniya-2026",
    );
  });
});
