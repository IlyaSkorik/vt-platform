import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { makeFestival } from "@/features/festival-catalog/lib/fixtures";
import { FestivalCard } from "./festival-card";

const NOW = new Date("2026-07-15T12:00:00Z");

function renderCard(festival = makeFestival()) {
  return render(
    <MemoryRouter>
      <FestivalCard festival={festival} now={NOW} />
    </MemoryRouter>,
  );
}

describe("FestivalCard", () => {
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
    renderCard(makeFestival({ id: "f1", status: "REGISTRATION_OPEN" }));
    const apply = screen.getByRole("link", { name: /подать заявку/i });
    expect(apply).toHaveAttribute("href", "/cabinet/competitions/f1/apply");
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
