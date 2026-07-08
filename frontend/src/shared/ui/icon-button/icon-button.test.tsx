import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Bell } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { IconButton } from "./icon-button";

describe("IconButton", () => {
  it("exposes its accessible name", () => {
    render(<IconButton icon={<Bell />} aria-label="Уведомления" />);
    expect(screen.getByRole("button", { name: "Уведомления" })).toBeInTheDocument();
  });

  it("invokes onClick when pressed", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<IconButton icon={<Bell />} aria-label="Уведомления" onClick={onClick} />);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<IconButton disabled icon={<Bell />} aria-label="Уведомления" onClick={onClick} />);
    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is busy while loading", () => {
    render(<IconButton loading icon={<Bell />} aria-label="Уведомления" />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
  });

  it("forwards a ref to the underlying button element", () => {
    const ref = vi.fn();
    render(<IconButton ref={ref} icon={<Bell />} aria-label="Уведомления" />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });
});
