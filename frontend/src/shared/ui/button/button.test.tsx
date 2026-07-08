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

  it.each([
    "primary",
    "secondary",
    "outline",
    "ghost",
    "danger",
    "success",
  ] as const)("renders the %s variant", (variant) => {
    render(<Button variant={variant}>Кнопка</Button>);
    expect(screen.getByRole("button", { name: "Кнопка" })).toBeInTheDocument();
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

  it("is disabled and busy while loading", () => {
    render(<Button loading>Загрузка</Button>);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("does not fire onClick while loading", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button loading onClick={onClick}>
        Загрузка
      </Button>,
    );
    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("supports keyboard activation via Enter", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Ввод</Button>);
    screen.getByRole("button").focus();
    await user.keyboard("{Enter}");
    expect(onClick).toHaveBeenCalledOnce();
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

  it("forwards a ref to the underlying button element", () => {
    const ref = vi.fn();
    render(<Button ref={ref}>Реф</Button>);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });
});
