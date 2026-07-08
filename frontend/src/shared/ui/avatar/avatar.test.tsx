import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Avatar } from "./avatar";

// jsdom never fires image load/error events, so Radix keeps the fallback
// mounted. We assert on structure and fallback rendering rather than the swap.
describe("Avatar", () => {
  it("renders the fallback initials", () => {
    render(<Avatar fallback="ИП" />);
    expect(screen.getByText("ИП")).toBeInTheDocument();
  });

  it("renders a node fallback", () => {
    render(<Avatar fallback={<span data-testid="node-fallback">★</span>} />);
    expect(screen.getByTestId("node-fallback")).toBeInTheDocument();
  });

  it.each(["xs", "sm", "md", "lg", "xl"] as const)("renders the %s size", (size) => {
    render(<Avatar size={size} fallback="XX" />);
    expect(screen.getByText("XX")).toBeInTheDocument();
  });

  it("forwards a ref to the root element", () => {
    const ref = vi.fn();
    render(<Avatar ref={ref} fallback="РФ" />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLSpanElement));
  });

  it("merges a custom className on the root", () => {
    const { container } = render(<Avatar className="custom-avatar" fallback="КЛ" />);
    expect(container.querySelector("[data-slot='avatar']")).toHaveClass("custom-avatar");
  });
});
