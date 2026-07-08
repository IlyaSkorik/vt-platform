import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Skeleton } from "./skeleton";

describe("Skeleton", () => {
  it("renders and is hidden from assistive tech by default", () => {
    render(<Skeleton data-testid="skeleton" />);
    const el = screen.getByTestId("skeleton");
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("aria-hidden", "true");
  });

  it.each(["text", "circle", "rect"] as const)("renders the %s variant", (variant) => {
    render(<Skeleton data-testid="skeleton" variant={variant} />);
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
  });

  it("allows overriding aria-hidden", () => {
    render(<Skeleton data-testid="skeleton" aria-hidden={false} />);
    expect(screen.getByTestId("skeleton")).toHaveAttribute("aria-hidden", "false");
  });

  it("merges a custom className for sizing", () => {
    render(<Skeleton data-testid="skeleton" className="h-10 w-10" />);
    expect(screen.getByTestId("skeleton")).toHaveClass("h-10", "w-10");
  });

  it("forwards a ref to the underlying element", () => {
    const ref = vi.fn();
    render(<Skeleton ref={ref} />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLDivElement));
  });
});
