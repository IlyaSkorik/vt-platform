/**
 * Что консоль оператора вообще умеет продавать.
 *
 * Тест на один класс ошибок, который уже случился: модуль появляется на сервере,
 * в консоль его не дописывают — и подключить его нельзя никому, потому что
 * выключателя просто нет, а «Полный доступ» собирается из того же списка.
 */
import { describe, expect, it } from "vitest";
import { OrganizationModule } from "@/shared/api/generated/model";
import { FULL_ACCESS_PRESET, MODULE_LABELS, PLATFORM_MODULES } from "./platform-api";

const SERVER_MODULES = Object.values(OrganizationModule);

describe("the module switchboard's vocabulary", () => {
  it("offers every module the server knows", () => {
    expect([...PLATFORM_MODULES].sort()).toEqual([...SERVER_MODULES].sort());
  });

  it("names every one of them in Russian", () => {
    for (const module of SERVER_MODULES) {
      expect(MODULE_LABELS[module]?.trim()).toBeTruthy();
    }
  });

  it("hands all of them over on full access", () => {
    expect([...FULL_ACCESS_PRESET.modules].sort()).toEqual([...SERVER_MODULES].sort());
  });

  it("keeps reviews switchable — the module this test was written for", () => {
    expect(PLATFORM_MODULES).toContain("REVIEWS");
    expect(FULL_ACCESS_PRESET.modules).toContain("REVIEWS");
  });
});
