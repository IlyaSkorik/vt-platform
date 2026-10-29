import { describe, expect, it } from "vitest";

import { livePollInterval, type PublicProgram } from "./api";

/**
 * Who keeps polling while nobody is looking.
 *
 * The rule costs nothing when it is right and is invisible when it is wrong — a stage
 * display that quietly stopped refreshing looks exactly like a programme that has not
 * moved — so it is pinned down here rather than left to a reviewer's reading.
 */

const program = (controlsRunningOrder: boolean): PublicProgram => ({
  name: "Программа первого дня",
  slug: "Sound2345",
  competitionTitle: "Взлёт талантов",
  nomination: "Вокал",
  startsAt: "2026-09-01T10:00:00Z",
  totalSeconds: 1380,
  controlsRunningOrder,
  columns: [{ key: "TIME", label: "Время", custom: false, sensitive: false }],
  rows: [],
});

describe("livePollInterval", () => {
  it("polls every few seconds while the page is visible", () => {
    expect(livePollInterval(program(false), false)).toBeGreaterThan(0);
    expect(livePollInterval(program(true), false)).toBeGreaterThan(0);
  });

  it("stops a hidden viewer's screen — it shows nobody anything", () => {
    expect(livePollInterval(program(false), true)).toBe(false);
  });

  it("keeps a hidden host's screen going — nothing brings a stage display to the front", () => {
    expect(livePollInterval(program(true), true)).toBeGreaterThan(0);
  });

  it("polls before the first read lands, since the edition may turn out to be the host's", () => {
    expect(livePollInterval(undefined, true)).toBeGreaterThan(0);
  });
});
