import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Divider } from "./divider";

describe("Divider", () => {
  it("is decorative by default (no separator role)", () => {
    render(<Divider />);
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  it("exposes the separator role when not decorative", () => {
    render(<Divider decorative={false} />);
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });

  it("reflects a vertical orientation", () => {
    render(<Divider decorative={false} orientation="vertical" />);
    expect(screen.getByRole("separator")).toHaveAttribute("aria-orientation", "vertical");
  });

  it("renders a centred label", () => {
    render(<Divider label="или" />);
    expect(screen.getByText("или")).toBeInTheDocument();
  });

  it("merges a custom className", () => {
    const { container } = render(<Divider className="custom-divider" />);
    expect(container.querySelector("[data-slot='divider']")).toHaveClass("custom-divider");
  });

  it("forwards a ref to the underlying element", () => {
    const ref = vi.fn();
    render(<Divider ref={ref} decorative={false} />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLElement));
  });
});
