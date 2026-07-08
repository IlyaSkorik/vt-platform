import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it } from "vitest";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

function Fixture({ defaultValue = "account" }: { defaultValue?: string }) {
  return (
    <Tabs defaultValue={defaultValue}>
      <TabsList>
        <TabsTrigger value="account">Аккаунт</TabsTrigger>
        <TabsTrigger value="password">Пароль</TabsTrigger>
        <TabsTrigger value="disabled" disabled>
          Недоступно
        </TabsTrigger>
      </TabsList>
      <TabsContent value="account">Панель аккаунта</TabsContent>
      <TabsContent value="password">Панель пароля</TabsContent>
      <TabsContent value="disabled">Недоступная панель</TabsContent>
    </Tabs>
  );
}

describe("Tabs", () => {
  it("renders the default tab content", () => {
    render(<Fixture />);
    expect(screen.getByText("Панель аккаунта")).toBeInTheDocument();
    expect(screen.queryByText("Панель пароля")).not.toBeInTheDocument();
  });

  it("exposes tab and tablist roles", () => {
    render(<Fixture />);
    expect(screen.getByRole("tablist")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
  });

  it("switches content on click", async () => {
    const user = userEvent.setup();
    render(<Fixture />);
    await user.click(screen.getByRole("tab", { name: "Пароль" }));
    expect(screen.getByText("Панель пароля")).toBeInTheDocument();
  });

  it("marks the active tab as selected", async () => {
    const user = userEvent.setup();
    render(<Fixture />);
    const passwordTab = screen.getByRole("tab", { name: "Пароль" });
    await user.click(passwordTab);
    expect(passwordTab).toHaveAttribute("aria-selected", "true");
  });

  it("navigates between tabs with arrow keys", async () => {
    const user = userEvent.setup();
    render(<Fixture />);
    const accountTab = screen.getByRole("tab", { name: "Аккаунт" });
    accountTab.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Пароль" })).toHaveFocus();
  });

  it("disables a disabled trigger", () => {
    render(<Fixture />);
    expect(screen.getByRole("tab", { name: "Недоступно" })).toBeDisabled();
  });

  it("forwards a ref to the trigger element", () => {
    const ref = createRef<HTMLButtonElement>();
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger ref={ref} value="a">
            А
          </TabsTrigger>
        </TabsList>
        <TabsContent value="a">Контент</TabsContent>
      </Tabs>,
    );
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});
