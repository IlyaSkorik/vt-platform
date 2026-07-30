import { describe, expect, it } from "vitest";

import { formatPersonName } from "./person-name";

describe("formatPersonName", () => {
  it("raises the first letter and lowers the rest", () => {
    expect(formatPersonName("иванов")).toBe("Иванов");
    expect(formatPersonName("ИВАНОВ")).toBe("Иванов");
    expect(formatPersonName("иВаНоВ")).toBe("Иванов");
  });

  it("capitalises every part of a compound surname", () => {
    expect(formatPersonName("петров-водкин")).toBe("Петров-Водкин");
    expect(formatPersonName("О'НИЛ")).toBe("О'Нил");
    expect(formatPersonName("анна мария")).toBe("Анна Мария");
  });

  it("trims and collapses stray whitespace", () => {
    expect(formatPersonName("  иванов  ")).toBe("Иванов");
    expect(formatPersonName("анна   мария")).toBe("Анна Мария");
    expect(formatPersonName("   ")).toBe("");
  });

  it("leaves latin names in the same shape", () => {
    expect(formatPersonName("jOHN")).toBe("John");
  });
});
