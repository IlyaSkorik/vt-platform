import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("renders its children", () => {
    render(<Button>Отправить</Button>);
    expect(screen.getByRole("button", { name: "Отправить" })).toBeInTheDocument();
  });

  it("defaults to type=button to avoid accidental form submits", () => {
    render(<Button>Действие</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });

  it("invokes onClick when pressed", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Клик</Button>);
    await user.click(screen.getByRole("button", { name: "Клик" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button disabled onClick={onClick}>
        Заблокировано
      </Button>,
    );
    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders as a child element when asChild is set", () => {
    render(
      <Button asChild>
        <a href="/dashboard">Панель</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Панель" });
    expect(link).toHaveAttribute("href", "/dashboard");
    expect(link).toHaveAttribute("data-slot", "button");
  });
});
