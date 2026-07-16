import { describe, expect, it } from "vitest";

import type { DirectoryTeacher } from "./index";
import { toCreditTeacherRequest } from "./lib";

function teacher(overrides: Partial<DirectoryTeacher> = {}): DirectoryTeacher {
  return {
    id: "01900000-0000-7000-8000-0000000000aa",
    ownerId: "01900000-0000-7000-8000-0000000000bb",
    firstName: "Елена",
    lastName: "Соколова",
    middleName: "Ивановна",
    displayName: "Соколова Елена Ивановна",
    role: "Хореограф",
    email: "elena@school.ru",
    phone: null,
    status: "ACTIVE",
    archivedAt: null,
    createdAt: "2026-07-13T00:00:00Z",
    updatedAt: "2026-07-13T00:00:00Z",
    ...overrides,
  };
}

describe("toCreditTeacherRequest", () => {
  it("credits by directory id and carries the name/role snapshot", () => {
    expect(toCreditTeacherRequest(teacher())).toEqual({
      teacherDirectoryId: "01900000-0000-7000-8000-0000000000aa",
      firstName: "Елена",
      lastName: "Соколова",
      middleName: "Ивановна",
      role: "Хореограф",
    });
  });

  it("passes a null middle name through", () => {
    expect(toCreditTeacherRequest(teacher({ middleName: null })).middleName).toBeNull();
  });
});
