import type { VerifiedDiploma } from "./types";

/** A fully-populated verified diploma; override only what a test is about. */
export function makeVerifiedDiploma(overrides: Partial<VerifiedDiploma> = {}): VerifiedDiploma {
  return {
    number: "VT-2026-000001",
    participantName: "Иванов Иван",
    // A solo entry: only an individual diploma names a member of a collective.
    memberName: null,
    competitionTitle: "Восходящие таланты",
    competitionDate: "15.05.2026",
    nomination: "Вокал",
    performance: "Этюд",
    teacher: "Петрова Мария",
    organization: "ДШИ №1",
    degree: "Лауреат I степени",
    issueDate: "2026-05-20T12:00:00Z",
    officialPdfUrl: "/media/diplomas/official/VT-2026-000001.pdf",
    verified: true,
    ...overrides,
  };
}
