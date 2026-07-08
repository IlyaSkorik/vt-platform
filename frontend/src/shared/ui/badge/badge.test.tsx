import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Badge } from "./badge";

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge>Активен</Badge>);
    expect(screen.getByText("Активен")).toBeInTheDocument();
  });

  it.each([
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
    "info",
    "outline",
    "neutral",
  ] as const)("renders the %s variant", (variant) => {
    render(<Badge variant={variant}>Метка</Badge>);
    expect(screen.getByText("Метка")).toBeInTheDocument();
  });

  it.each(["sm", "md"] as const)("renders the %s size", (size) => {
    render(<Badge size={size}>Размер</Badge>);
    expect(screen.getByText("Размер")).toBeInTheDocument();
  });

  it("renders a leading icon", () => {
    render(<Badge icon={<svg data-testid="badge-icon" />}>С иконкой</Badge>);
    expect(screen.getByTestId("badge-icon")).toBeInTheDocument();
  });

  it("renders a status dot when requested", () => {
    const { container } = render(<Badge dot>С точкой</Badge>);
    expect(container.querySelector("[aria-hidden='true']")).toBeInTheDocument();
  });

  it("forwards a ref to the underlying span element", () => {
    const ref = vi.fn();
    render(<Badge ref={ref}>Реф</Badge>);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLSpanElement));
  });

  it("merges a custom className", () => {
    render(<Badge className="custom-badge">Класс</Badge>);
    expect(screen.getByText("Класс")).toHaveClass("custom-badge");
  });
});
