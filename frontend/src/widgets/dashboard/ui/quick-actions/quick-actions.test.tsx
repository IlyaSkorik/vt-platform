import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { QuickActions } from "./quick-actions";

describe("QuickActions", () => {
  it("renders every primary shortcut as a link to its route", () => {
    render(
      <MemoryRouter>
        <QuickActions />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /Регистрация участника/ })).toHaveAttribute(
      "href",
      "/participants",
    );
    expect(screen.getByRole("link", { name: /Создать фестиваль/ })).toHaveAttribute(
      "href",
      "/competitions",
    );
    expect(screen.getByRole("link", { name: /Заявки/ })).toHaveAttribute("href", "/applications");
    expect(screen.getAllByRole("link")).toHaveLength(5);
  });
});
