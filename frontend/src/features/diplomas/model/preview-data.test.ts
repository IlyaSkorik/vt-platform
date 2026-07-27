import { describe, expect, it } from "vitest";
import { PARTICIPANT_DISPLAY_NAME, TEACHER_DISPLAY_NAME } from "./binding";
import { resolvePreviewValue } from "./preview-data";

describe("resolvePreviewValue", () => {
  it("states the teacher's role on a diploma", () => {
    // A diploma credits a teacher in a stated capacity, and generation prints it.
    expect(resolvePreviewValue(TEACHER_DISPLAY_NAME, "individual", "DIPLOMA")).toBe(
      "Педагог: Петрова Мария Сергеевна",
    );
  });

  it("names the teacher without the role on a thank-you letter", () => {
    // The bug this covers: the sample always carried "Педагог: ", so a letter was
    // designed around a label its own generation drops.
    expect(resolvePreviewValue(TEACHER_DISPLAY_NAME, "individual", "THANK_YOU")).toBe(
      "Петрова Мария Сергеевна",
    );
  });

  it("keeps the role when the kind is unknown or unstated", () => {
    // A client running behind the backend shows the fuller form rather than
    // silently dropping information.
    expect(resolvePreviewValue(TEACHER_DISPLAY_NAME, "individual")).toBe(
      "Педагог: Петрова Мария Сергеевна",
    );
    expect(resolvePreviewValue(TEACHER_DISPLAY_NAME, "individual", "CERTIFICATE")).toBe(
      "Педагог: Петрова Мария Сергеевна",
    );
  });

  it("resolves the teacher the same way for a collective", () => {
    expect(resolvePreviewValue(TEACHER_DISPLAY_NAME, "collective", "THANK_YOU")).toBe(
      "Петрова Мария Сергеевна",
    );
  });

  it("still varies the performer by mode", () => {
    expect(resolvePreviewValue(PARTICIPANT_DISPLAY_NAME, "individual", "THANK_YOU")).toBe(
      "Иванов Иван Иванович",
    );
    expect(resolvePreviewValue(PARTICIPANT_DISPLAY_NAME, "collective", "THANK_YOU")).toBe(
      "Ансамбль «Созвездие»",
    );
  });
});
