import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Search } from "lucide-react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState title="Нет данных" />);
    expect(screen.getByText("Нет данных")).toBeInTheDocument();
  });

  it("renders the description when provided", () => {
    render(<EmptyState title="Пусто" description="Добавьте первую запись" />);
    expect(screen.getByText("Добавьте первую запись")).toBeInTheDocument();
  });

  it("exposes a region role", () => {
    render(<EmptyState title="Ничего не найдено" />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("renders a custom icon", () => {
    render(<EmptyState title="Поиск" icon={<Search data-testid="search-icon" />} />);
    expect(screen.getByTestId("search-icon")).toBeInTheDocument();
  });

  it("renders and wires the action slot", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <EmptyState
        title="Пусто"
        action={
          <button type="button" onClick={onClick}>
            Создать
          </button>
        }
      />,
    );
    await user.click(screen.getByRole("button", { name: "Создать" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("forwards a ref to the root element", () => {
    const ref = createRef<HTMLElement>();
    render(<EmptyState ref={ref} title="Пусто" />);
    expect(ref.current).toBeInstanceOf(HTMLElement);
    expect(ref.current?.tagName).toBe("SECTION");
  });
});
