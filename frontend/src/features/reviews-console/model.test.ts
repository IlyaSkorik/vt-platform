import { describe, expect, it } from "vitest";

import type { Review } from "./api";
import { authorLabel, publicReviewUrl } from "./model";

function review(overrides: Partial<Review> = {}): Review {
  return {
    id: "r-1",
    authorName: null,
    text: "Спасибо!",
    photos: [],
    competitionId: null,
    competitionTitle: null,
    submittedAt: "2026-09-19T10:00:00Z",
    consentType: "data_processing",
    consentVersion: "1.0",
    consentAcceptedAt: "2026-09-19T10:00:00Z",
    organizationId: "org-1",
    organizationName: null,
    ...overrides,
  };
}

describe("the public link", () => {
  it("is absolute, because it goes onto a banner", () => {
    expect(publicReviewUrl("AbX82Kqm9p", "https://vzlettalantov.by")).toBe(
      "https://vzlettalantov.by/reviews/AbX82Kqm9p",
    );
  });
});

describe("how a note is signed", () => {
  it("says so plainly when it is not signed at all", () => {
    expect(authorLabel(review())).toBe("Без подписи");
  });

  it("treats a name of nothing but spaces as no name", () => {
    expect(authorLabel(review({ authorName: "   " }))).toBe("Без подписи");
  });

  it("prints the name when there is one", () => {
    expect(authorLabel(review({ authorName: "Мария" }))).toBe("Мария");
  });
});
