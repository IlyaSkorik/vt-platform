import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "./drawer";
import type { DrawerSide } from "./types";

beforeAll(() => {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.scrollIntoView = () => {};
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function Example({ side }: { side?: DrawerSide }) {
  return (
    <Drawer>
      <DrawerTrigger>Открыть</DrawerTrigger>
      <DrawerContent {...(side != null ? { side } : {})}>
        <DrawerHeader>
          <DrawerTitle>Панель</DrawerTitle>
          <DrawerDescription>Описание панели.</DrawerDescription>
        </DrawerHeader>
        <DrawerClose>Закрыть панель</DrawerClose>
      </DrawerContent>
    </Drawer>
  );
}

describe("Drawer", () => {
  it("is closed by default", () => {
    render(<Example />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens when the trigger is clicked", async () => {
    const user = userEvent.setup();
    render(<Example />);
    await user.click(screen.getByRole("button", { name: "Открыть" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Панель")).toBeInTheDocument();
  });

  it("closes when Escape is pressed", async () => {
    const user = userEvent.setup();
    render(<Example />);
    await user.click(screen.getByRole("button", { name: "Открыть" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it.each([
    "left",
    "right",
    "top",
    "bottom",
  ] as const)("reflects the %s side on the content", async (side) => {
    const user = userEvent.setup();
    render(<Example side={side} />);
    await user.click(screen.getByRole("button", { name: "Открыть" }));
    expect(screen.getByRole("dialog")).toHaveAttribute("data-side", side);
  });

  it("defaults to the right side", async () => {
    const user = userEvent.setup();
    render(<Example />);
    await user.click(screen.getByRole("button", { name: "Открыть" }));
    expect(screen.getByRole("dialog")).toHaveAttribute("data-side", "right");
  });
});
