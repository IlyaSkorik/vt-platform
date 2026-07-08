import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Alert } from "./alert";

describe("Alert", () => {
  it("renders its title and description", () => {
    render(
      <Alert title="Внимание" variant="info">
        Проверьте введённые данные.
      </Alert>,
    );
    expect(screen.getByText("Внимание")).toBeInTheDocument();
    expect(screen.getByText("Проверьте введённые данные.")).toBeInTheDocument();
  });

  it.each([
    "info",
    "success",
    "warning",
    "danger",
  ] as const)("renders the %s variant", (variant) => {
    render(
      <Alert variant={variant} title="Статус">
        Сообщение
      </Alert>,
    );
    expect(screen.getByText("Статус")).toBeInTheDocument();
  });

  it("uses role=alert for critical variants", () => {
    render(<Alert variant="danger" title="Ошибка" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("uses role=status for non-critical variants", () => {
    render(<Alert variant="success" title="Готово" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders a dismiss button and invokes onDismiss when clicked", async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    render(<Alert title="Уведомление" dismissible onDismiss={onDismiss} />);
    await user.click(screen.getByRole("button", { name: "Закрыть" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("does not render a dismiss button by default", () => {
    render(<Alert title="Уведомление" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders no icon when icon is null", () => {
    const { container } = render(<Alert title="Без иконки" icon={null} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("forwards a ref to the root element", () => {
    const ref = vi.fn();
    render(<Alert ref={ref} title="Реф" />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLDivElement));
  });
});
