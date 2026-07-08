import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";

beforeAll(() => {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.scrollIntoView = () => {};
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function Example() {
  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger>Наведите</TooltipTrigger>
        <TooltipContent>Подсказка</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

describe("Tooltip", () => {
  it("renders the trigger", () => {
    render(<Example />);
    expect(screen.getByRole("button", { name: "Наведите" })).toBeInTheDocument();
  });

  it("is hidden until the trigger is focused", () => {
    render(<Example />);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows on keyboard focus of the trigger", async () => {
    const user = userEvent.setup();
    render(<Example />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Наведите" })).toHaveFocus();
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Подсказка");
  });

  it("hides again when focus leaves the trigger", async () => {
    const user = userEvent.setup();
    render(<Example />);
    await user.tab();
    expect(await screen.findByRole("tooltip")).toBeInTheDocument();
    await user.tab();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
