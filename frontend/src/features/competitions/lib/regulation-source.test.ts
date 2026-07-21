import { describe, expect, it } from "vitest";
import { detectRegulationSource } from "./regulation-source";

describe("detectRegulationSource", () => {
  it("treats absolute URLs as links", () => {
    expect(detectRegulationSource("https://docs.google.com/document/d/abc/edit")).toBe("link");
    expect(detectRegulationSource("http://example.com/reg.pdf")).toBe("link");
  });

  it("treats stored media paths and empty values as files", () => {
    expect(detectRegulationSource("/media/competitions/1/regulations/x.pdf")).toBe("file");
    expect(detectRegulationSource("")).toBe("file");
    expect(detectRegulationSource(null)).toBe("file");
    expect(detectRegulationSource(undefined)).toBe("file");
  });
});
