import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "@/app/providers";
import { makeFestival } from "@/features/festival-catalog/lib/fixtures";
import { FestivalCard } from "./festival-card";

// The card reads the session to decide where "Подать заявку" points, so it needs an auth
// context. Mocked rather than wrapped in a real `AuthProvider`: that would drag a
// QueryClient and the token store into what is a unit test of one card's markup, and it
// would make the session something to set up rather than something to assert on.
vi.mock("@/app/providers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/providers")>()),
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

function signedIn(isAuthenticated: boolean): void {
  mockedUseAuth.mockReturnValue({ isAuthenticated } as unknown as ReturnType<typeof useAuth>);
}

const NOW = new Date("2026-07-15T12:00:00Z");

function renderCard(festival = makeFestival()) {
  return render(
    <MemoryRouter>
      <FestivalCard festival={festival} now={NOW} />
    </MemoryRouter>,
  );
}

describe("FestivalCard", () => {
  beforeEach(() => {
    signedIn(true);
  });

  it("renders the core competition facts", () => {
    renderCard(
      makeFestival({
        title: "Весенний вокал",
        organizer: { id: "o", name: "Дом талантов", logo: null },
        city: "Минск",
      }),
    );
    expect(screen.getByText("Весенний вокал")).toBeInTheDocument();
    expect(screen.getByText("Дом талантов")).toBeInTheDocument();
    expect(screen.getByText("Минск")).toBeInTheDocument();
  });

  it("shows an enabled Apply link when registration is open", () => {
    // Addressed by slug, not id: that is the readable URL the festival is linked by,
    // and the id is only the fallback for a competition that predates slugs.
    renderCard(makeFestival({ id: "f1", slug: "vesenniy-vokal", status: "REGISTRATION_OPEN" }));
    const apply = screen.getByRole("link", { name: /подать заявку/i });
    expect(apply).toHaveAttribute("href", "/cabinet/competitions/vesenniy-vokal/apply");
  });

  it("falls back to the id for a festival with no slug", () => {
    renderCard(makeFestival({ id: "f1", slug: null, status: "REGISTRATION_OPEN" }));
    expect(screen.getByRole("link", { name: /подать заявку/i })).toHaveAttribute(
      "href",
      "/cabinet/competitions/f1/apply",
    );
  });

  it("sends a visitor through login and back to the application", () => {
    // A public catalog card must not point an anonymous visitor straight at a cabinet
    // route: they would be bounced to login and lose the festival they had chosen.
    signedIn(false);
    renderCard(makeFestival({ id: "f1", slug: "vesenniy-vokal", status: "REGISTRATION_OPEN" }));
    expect(screen.getByRole("link", { name: /подать заявку/i })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent("/cabinet/competitions/vesenniy-vokal/apply")}`,
    );
  });

  it("hides Apply for completed festivals but keeps details", () => {
    renderCard(makeFestival({ status: "COMPLETED" }));
    expect(screen.queryByRole("link", { name: /подать заявку/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Подробнее" })).toBeInTheDocument();
  });

  it("renders a disabled action for coming-soon", () => {
    renderCard(makeFestival({ status: "COMING_SOON" }));
    const button = screen.getByRole("button", { name: /регистрация скоро/i });
    expect(button).toBeDisabled();
  });

  it("shows a 'from' price when multiple prices exist", () => {
    renderCard(makeFestival({ pricing: { amountFrom: "30", currency: "BYN", multiple: true } }));
    expect(screen.getByText("от 30 BYN")).toBeInTheDocument();
  });

  it("flags competitions closing soon", () => {
    renderCard(makeFestival({ status: "REGISTRATION_OPEN", registrationEnd: "2026-07-18" }));
    expect(screen.getByText("Скоро закрытие")).toBeInTheDocument();
  });
});
