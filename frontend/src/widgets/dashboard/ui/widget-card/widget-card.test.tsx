import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WidgetCard } from "./widget-card";

const baseProps = {
  title: "Виджет",
  loadingSkeleton: <div data-testid="skeleton">skeleton</div>,
  emptyTitle: "Пусто",
  children: <div data-testid="content">content</div>,
} as const;

describe("WidgetCard", () => {
  it("renders the skeleton and marks the region busy while loading", () => {
    render(<WidgetCard {...baseProps} status="loading" />);
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    expect(screen.getByLabelText("Виджет")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByTestId("content")).not.toBeInTheDocument();
  });

  it("renders the empty state", () => {
    render(<WidgetCard {...baseProps} status="empty" emptyDescription="Нет записей" />);
    expect(screen.getByText("Пусто")).toBeInTheDocument();
    expect(screen.getByText("Нет записей")).toBeInTheDocument();
  });

  it("renders an error state with a working retry", async () => {
    const onRetry = vi.fn();
    render(<WidgetCard {...baseProps} status="error" onRetry={onRetry} />);
    expect(screen.getByText("Не удалось загрузить данные")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders children only in the success state", () => {
    render(<WidgetCard {...baseProps} status="success" headerAction={<span>badge</span>} />);
    expect(screen.getByTestId("content")).toBeInTheDocument();
    expect(screen.getByText("badge")).toBeInTheDocument();
  });
});
