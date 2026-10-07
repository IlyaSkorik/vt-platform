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
        city: "Минск",
        modes: ["IN_PERSON"],
        categories: ["Вокал"],
      }),
    );
    expect(screen.getByText("Весенний вокал")).toBeInTheDocument();
    // Place and format are printed as one line, the way the frame has it.
    expect(screen.getByText("Минск, Очно")).toBeInTheDocument();
    expect(screen.getByText("Вокал")).toBeInTheDocument();
  });

  it("drops the comma when the festival has no city", () => {
    renderCard(makeFestival({ city: null, modes: ["ONLINE"] }));
    expect(screen.getByText("Онлайн")).toBeInTheDocument();
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

  // The action slot is never empty: a festival that cannot be applied to says why
  // in the button's place, so the card keeps its height and the reader gets the
  // reason instead of a gap where something used to be.
  it.each([
    ["COMPLETED", "Фестиваль завершён"],
    ["RUNNING", "Регистрация закрыта"],
    ["REGISTRATION_CLOSED", "Регистрация закрыта"],
    ["COMING_SOON", "Регистрация скоро"],
  ])("states the reason instead of an Apply link for %s", (status, reason) => {
    renderCard(makeFestival({ status }));
    expect(screen.queryByRole("link", { name: /подать заявку/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: reason })).toBeDisabled();
    // And the one thing that still leads somewhere stays where it was.
    expect(screen.getByRole("link", { name: "Подробнее" })).toBeInTheDocument();
  });

  // The tile deliberately carries four facts and two actions and nothing else —
  // see the note on the component. These assert the *absence* of what it used to
  // show, so that putting any of it back is a decision and not a drift: all of it
  // is on the festival's own page, one click away.
  it("carries no price, status badge or closing-soon flag", () => {
    renderCard(
      makeFestival({
        status: "REGISTRATION_OPEN",
        registrationEnd: "2026-07-18",
        pricing: { amountFrom: "30", currency: "BYN", multiple: true },
        organizer: { id: "o", name: "Дом талантов", logo: null },
      }),
    );
    expect(screen.queryByText("от 30 BYN")).not.toBeInTheDocument();
    expect(screen.queryByText("Скоро закрытие")).not.toBeInTheDocument();
    expect(screen.queryByText("Дом талантов")).not.toBeInTheDocument();
  });
});
