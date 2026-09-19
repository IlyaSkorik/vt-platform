import { describe, expect, it } from "vitest";

import { photoProblem } from "./model";

function file(name: string, type: string, bytes: number): File {
  const blob = new Blob([new Uint8Array(bytes)], { type });
  return new File([blob], name, { type });
}

describe("what may be attached to a review", () => {
  it("accepts a photograph from a phone", () => {
    expect(photoProblem(file("hall.jpg", "image/jpeg", 1024))).toBeNull();
    expect(photoProblem(file("hall.heic", "image/heic", 1024))).toBeNull();
  });

  it("refuses something that is not a photograph, and names it", () => {
    const problem = photoProblem(file("rider.pdf", "application/pdf", 1024));

    expect(problem).toContain("rider.pdf");
  });

  it("refuses a file too heavy to be worth uploading over a hall's wifi", () => {
    const problem = photoProblem(file("raw.png", "image/png", 9 * 1024 * 1024));

    expect(problem).toContain("raw.png");
  });
});
