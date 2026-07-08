import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Spinner } from "./spinner";

describe("Spinner", () => {
  it("exposes the status role with a default accessible name", () => {
    render(<Spinner />);
    expect(screen.getByRole("status", { name: "Загрузка" })).toBeInTheDocument();
  });

  it("uses a custom accessible label", () => {
    render(<Spinner label="Отправка" />);
    expect(screen.getByRole("status", { name: "Отправка" })).toBeInTheDocument();
  });

  it.each(["xs", "sm", "md", "lg", "xl"] as const)("renders the %s size", (size) => {
    render(<Spinner size={size} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("merges a custom className", () => {
    render(<Spinner className="custom-spinner" />);
    expect(screen.getByRole("status")).toHaveClass("custom-spinner");
  });

  it("forwards a ref to the underlying element", () => {
    const ref = vi.fn();
    render(<Spinner ref={ref} />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLSpanElement));
  });
});
