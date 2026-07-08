import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Users } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { StatCard } from "./stat-card";

describe("StatCard", () => {
  it("renders the value and delta in the success state", () => {
    render(
      <StatCard
        label="Участники"
        icon={Users}
        tone="primary"
        status="success"
        value="1 284"
        delta="+12,5 %"
        trend="up"
      />,
    );
    expect(screen.getByText("1 284")).toBeInTheDocument();
    expect(screen.getByText("+12,5 %")).toBeInTheDocument();
  });

  it("marks the card busy and shows no value while loading", () => {
    render(<StatCard label="Участники" icon={Users} tone="primary" status="loading" />);
    expect(screen.getByLabelText("Участники")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("1 284")).not.toBeInTheDocument();
  });

  it("renders the empty label in the empty state", () => {
    render(
      <StatCard
        label="Финансы"
        icon={Users}
        tone="neutral"
        status="empty"
        emptyLabel="Нет данных"
      />,
    );
    expect(screen.getByText("Нет данных")).toBeInTheDocument();
  });

  it("surfaces a retry control in the error state", async () => {
    const onRetry = vi.fn();
    render(
      <StatCard label="Заявки" icon={Users} tone="warning" status="error" onRetry={onRetry} />,
    );
    expect(screen.getByText("Ошибка загрузки")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Повторить загрузку: Заявки" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
