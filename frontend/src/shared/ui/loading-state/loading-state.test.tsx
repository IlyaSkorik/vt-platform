import { render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it } from "vitest";
import { LoadingState } from "./loading-state";

describe("LoadingState", () => {
  it("renders a status region with the default accessible name", () => {
    render(<LoadingState />);
    expect(screen.getByRole("status", { name: "Загрузка" })).toBeInTheDocument();
  });

  it("renders a visible label when provided", () => {
    render(<LoadingState label="Загружаем данные" />);
    expect(screen.getByText("Загружаем данные")).toBeInTheDocument();
  });

  it("uses a custom screen-reader label", () => {
    render(<LoadingState srLabel="Идёт загрузка" />);
    expect(screen.getByRole("status", { name: "Идёт загрузка" })).toBeInTheDocument();
  });

  it.each(["sm", "md", "lg"] as const)("renders the %s size", (size) => {
    render(<LoadingState size={size} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("forwards a ref to the root element", () => {
    const ref = createRef<HTMLDivElement>();
    render(<LoadingState ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });
});
