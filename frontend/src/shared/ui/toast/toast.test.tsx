import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Toaster, toast } from "./toast";

describe("Toaster", () => {
  it("renders without crashing", () => {
    const { container } = render(<Toaster />);
    expect(container).toBeInTheDocument();
  });

  it("renders Sonner's notification region", () => {
    render(<Toaster />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("accepts theme and position overrides", () => {
    const { container } = render(<Toaster theme="dark" position="top-center" />);
    expect(container).toBeInTheDocument();
  });
});

describe("toast helper", () => {
  it("re-exports the sonner toast function", () => {
    expect(typeof toast).toBe("function");
  });

  it("exposes status variant helpers", () => {
    expect(typeof toast.success).toBe("function");
    expect(typeof toast.error).toBe("function");
    expect(typeof toast.warning).toBe("function");
    expect(typeof toast.info).toBe("function");
  });
});
