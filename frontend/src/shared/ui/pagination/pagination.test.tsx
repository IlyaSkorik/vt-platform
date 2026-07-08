import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { getPaginationRange } from "./get-pagination-range";
import { Pagination } from "./pagination";

describe("Pagination", () => {
  it("marks the current page with aria-current", () => {
    render(<Pagination page={3} pageCount={10} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Страница 3" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("renders an accessible navigation landmark", () => {
    render(<Pagination page={1} pageCount={5} onPageChange={vi.fn()} aria-label="Страницы" />);
    expect(screen.getByRole("navigation", { name: "Страницы" })).toBeInTheDocument();
  });

  it("disables the previous button on the first page", () => {
    render(<Pagination page={1} pageCount={10} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Предыдущая страница" })).toBeDisabled();
  });

  it("disables the next button on the last page", () => {
    render(<Pagination page={10} pageCount={10} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Следующая страница" })).toBeDisabled();
  });

  it("calls onPageChange with the clicked page number", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={1} pageCount={10} onPageChange={onPageChange} />);
    await user.click(screen.getByRole("button", { name: "Страница 2" }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("advances via the next button", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={4} pageCount={10} onPageChange={onPageChange} />);
    await user.click(screen.getByRole("button", { name: "Следующая страница" }));
    expect(onPageChange).toHaveBeenCalledWith(5);
  });

  it("shows an ellipsis for large page counts", () => {
    render(<Pagination page={5} pageCount={50} onPageChange={vi.fn()} />);
    expect(screen.getAllByText("…").length).toBeGreaterThan(0);
  });

  it("derives page count from total and pageSize", () => {
    render(<Pagination page={1} total={45} pageSize={10} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Страница 5" })).toBeInTheDocument();
  });

  it("renders nothing when there are no pages", () => {
    const { container } = render(<Pagination page={1} pageCount={0} onPageChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("forwards a ref to the nav element", () => {
    const ref = createRef<HTMLElement>();
    render(<Pagination ref={ref} page={1} pageCount={5} onPageChange={vi.fn()} />);
    expect(ref.current?.tagName).toBe("NAV");
  });
});

describe("getPaginationRange", () => {
  it("lists every page when the count is small", () => {
    expect(getPaginationRange(1, 5)).toEqual([1, 2, 3, 4, 5]);
  });

  it("truncates on the right near the start", () => {
    expect(getPaginationRange(2, 20)).toEqual([1, 2, 3, 4, 5, "ellipsis", 20]);
  });

  it("truncates on the left near the end", () => {
    expect(getPaginationRange(19, 20)).toEqual([1, "ellipsis", 16, 17, 18, 19, 20]);
  });

  it("truncates on both sides in the middle", () => {
    expect(getPaginationRange(10, 20)).toEqual([1, "ellipsis", 9, 10, 11, "ellipsis", 20]);
  });

  it("returns an empty range for non-positive counts", () => {
    expect(getPaginationRange(1, 0)).toEqual([]);
  });
});
