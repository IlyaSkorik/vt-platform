import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./card";

describe("Card", () => {
  it("renders a full composition with all parts", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Заголовок</CardTitle>
          <CardDescription>Описание карточки</CardDescription>
        </CardHeader>
        <CardContent>Содержимое</CardContent>
        <CardFooter>Подвал</CardFooter>
      </Card>,
    );
    expect(screen.getByRole("heading", { name: "Заголовок" })).toBeInTheDocument();
    expect(screen.getByText("Описание карточки")).toBeInTheDocument();
    expect(screen.getByText("Содержимое")).toBeInTheDocument();
    expect(screen.getByText("Подвал")).toBeInTheDocument();
  });

  it("renders the title as a semantic heading", () => {
    render(<CardTitle>Название</CardTitle>);
    expect(screen.getByRole("heading", { level: 3, name: "Название" })).toBeInTheDocument();
  });

  it("merges custom classNames on each part", () => {
    const { container } = render(
      <Card className="c-root">
        <CardHeader className="c-header" />
        <CardContent className="c-content" />
        <CardFooter className="c-footer" />
      </Card>,
    );
    expect(container.querySelector("[data-slot='card']")).toHaveClass("c-root");
    expect(container.querySelector("[data-slot='card-header']")).toHaveClass("c-header");
    expect(container.querySelector("[data-slot='card-content']")).toHaveClass("c-content");
    expect(container.querySelector("[data-slot='card-footer']")).toHaveClass("c-footer");
  });

  it("forwards refs to each part", () => {
    const cardRef = vi.fn();
    const titleRef = vi.fn();
    render(
      <Card ref={cardRef}>
        <CardTitle ref={titleRef}>Реф</CardTitle>
      </Card>,
    );
    expect(cardRef).toHaveBeenCalledWith(expect.any(HTMLDivElement));
    expect(titleRef).toHaveBeenCalledWith(expect.any(HTMLHeadingElement));
  });
});
