import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { MOCK_COMPETITIONS } from "../../model/mock-data";
import { RecentCompetitionsView } from "./recent-competitions";

function renderView(props: Parameters<typeof RecentCompetitionsView>[0]) {
  return render(
    <MemoryRouter>
      <RecentCompetitionsView {...props} />
    </MemoryRouter>,
  );
}

describe("RecentCompetitionsView", () => {
  it("lists competitions with their status labels on success", () => {
    renderView({ status: "success", competitions: MOCK_COMPETITIONS });
    expect(screen.getByText("Весенний вокальный конкурс")).toBeInTheDocument();
    // "submission" status maps to the "Приём заявок" badge label.
    expect(screen.getByText("Приём заявок")).toBeInTheDocument();
  });

  it("renders the empty state when there are no competitions", () => {
    renderView({ status: "empty", competitions: [] });
    expect(screen.getByText("Нет конкурсов")).toBeInTheDocument();
  });

  it("renders an accessible link to the full registry", () => {
    renderView({ status: "success", competitions: MOCK_COMPETITIONS });
    expect(screen.getByRole("link", { name: "Все конкурсы" })).toHaveAttribute(
      "href",
      "/competitions",
    );
  });
});
