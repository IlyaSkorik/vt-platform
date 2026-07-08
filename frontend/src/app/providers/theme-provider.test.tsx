import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { THEME_STORAGE_KEY } from "@/shared/constants";
import { ThemeProvider, useTheme } from "./theme-provider";

function ThemeProbe(): React.JSX.Element {
  const { resolvedTheme, setTheme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button type="button" onClick={() => setTheme("dark")}>
        dark
      </button>
      <button type="button" onClick={toggleTheme}>
        toggle
      </button>
    </div>
  );
}

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
});

describe("ThemeProvider", () => {
  it("throws when useTheme is used outside the provider", () => {
    expect(() => render(<ThemeProbe />)).toThrow(/ThemeProvider/);
  });

  it("applies the dark class and persists the choice when set", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "dark" }));

    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("toggles back to light", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole("button", { name: "dark" }));
    await act(async () => {
      await user.click(screen.getByRole("button", { name: "toggle" }));
    });

    expect(screen.getByTestId("resolved")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
